import io
import json
import os
from datetime import datetime

import openpyxl
from crewai.tools import tool
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES_DRIVE = ["https://www.googleapis.com/auth/drive"]
SCOPES_SHEETS = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_ID_EXCLUSION = "1sz7xUM05y6xI-bj1Wz8jvmOzuIH7ZzCoEyECgqkZ9xc"
SHEET_ID_PRINCIPAL = "1yEWVIlazcfih3iymhICk3pY2jXwVAisgeZB8WVje8a0"
FOLDER_ARCHIVES = "1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh"

COLONNES = [
    "Email", "Prenom", "Nom", "Source",
    "A verifier", "Domaine", "Statut", "Extension", "Date insertion",
]


def _get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES_DRIVE
    )
    return build("drive", "v3", credentials=creds)


def _get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES_SHEETS
    )
    return build("sheets", "v4", credentials=creds)


def _download_bytes(service, file_id: str) -> bytes:
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return buf.getvalue()


def _lire_contacts_depuis_excel_drive(folder_id: str, filename: str) -> str:
    """
    Logique interne : télécharge le fichier Excel depuis Drive, retourne un JSON array.
    Appelé par le @tool homonyme et par traiter_liste_contacts dans pipeline_tools.
    """
    service = _get_drive_service()

    results = service.files().list(
        q=(
            f"'{folder_id}' in parents "
            f"and name='{filename}' "
            "and trashed=false"
        ),
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])

    if not files:
        # Chercher aussi avec extension .xlsx si non trouvé exact
        results2 = service.files().list(
            q=(
                f"'{folder_id}' in parents "
                f"and name contains 'ListeContacts_Lin_Out' "
                "and trashed=false"
            ),
            fields="files(id, name)",
        ).execute()
        files = results2.get("files", [])

    if not files:
        return json.dumps(
            {"erreur": f"Fichier '{filename}' introuvable dans le dossier {folder_id}."}
        )

    data = _download_bytes(service, files[0]["id"])

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return json.dumps({"erreur": "Fichier Excel vide."})

    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    contacts = []
    for row in rows[1:]:
        obj = {headers[i]: (str(row[i]).strip() if row[i] is not None else "")
               for i in range(len(headers))}
        email = obj.get("Email", "").strip().lower()
        if "@" in email:
            obj["Email"] = email
            contacts.append(obj)

    return json.dumps(contacts, ensure_ascii=False)


@tool("Lire les contacts depuis un fichier Excel Google Drive")
def lire_contacts_depuis_excel_drive(folder_id: str, filename: str) -> str:
    """
    Télécharge le fichier Excel (filename) depuis le dossier Drive folder_id
    et retourne tous les contacts sous forme de JSON array d'objets.
    Chaque objet a les clés : Email, Prenom, Nom, Source, A verifier,
    Domaine, Statut, Extension, Date insertion.
    Les lignes sans Email valide sont ignorées.
    """
    return _lire_contacts_depuis_excel_drive(folder_id, filename)


def _lire_liste_exclusion() -> str:
    """
    Logique interne : lit le Google Sheet ListeExclusion, retourne un JSON array d'emails.
    Appelé par le @tool homonyme et par traiter_liste_contacts dans pipeline_tools.
    Si le Sheet est inaccessible (403), retourne une liste vide (aucune exclusion appliquée).
    """
    try:
        service = _get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID_EXCLUSION,
            range="A:A",
        ).execute()
        rows = result.get("values", [])
    except Exception:
        return json.dumps([])

    exclusions = []
    for row in rows[1:]:  # ligne 0 = en-tête "Emails exclus"
        if row and str(row[0]).strip():
            exclusions.append(str(row[0]).strip().lower())

    return json.dumps(exclusions, ensure_ascii=False)


@tool("Lire la liste des emails exclus depuis Google Sheets")
def lire_liste_exclusion() -> str:
    """
    Lit le Google Sheet ListeExclusion (colonne 'Emails exclus', colonne A)
    et retourne un JSON array des adresses email à exclure.
    """
    return _lire_liste_exclusion()


def _creer_excel_nettoye_dans_drive(
    contacts_json: str,
    exclusions_json: str,
    dest_folder_id: str,  # conservé pour compatibilité API, non utilisé
) -> str:
    """
    Logique interne : nettoie les contacts et écrit le résultat dans un nouvel onglet
    du Google Sheet principal (SHEET_ID_PRINCIPAL).
    Les comptes de service Google n'ayant pas de quota Drive, la création de fichiers
    Drive est impossible — on écrit dans un onglet dédié du Sheet existant.
    """
    contacts = json.loads(contacts_json)
    exclusions = set(json.loads(exclusions_json))

    nb_initial = len(contacts)

    # Passe 1 — supprimer lignes A verifier == 1
    contacts = [
        c for c in contacts
        if str(c.get("A verifier", "")).strip() != "1"
    ]
    nb_apres_averifier = len(contacts)

    # Passe 2 — supprimer emails exclus
    contacts = [
        c for c in contacts
        if c.get("Email", "").strip().lower() not in exclusions
    ]
    nb_apres_exclusion = len(contacts)

    # Passe 3 — dédoublonner sur Email
    vus = set()
    uniques = []
    for c in contacts:
        email = c.get("Email", "").strip().lower()
        if email and email not in vus:
            vus.add(email)
            uniques.append(c)
    contacts = uniques
    nb_final = len(contacts)

    TAB_FINAL = "ListeContacts_Lin_Out_FINAL"
    service = _get_sheets_service()

    # Vider l'onglet FINAL avant d'écrire (chaque exécution repart de zéro)
    try:
        service.spreadsheets().values().clear(
            spreadsheetId=SHEET_ID_PRINCIPAL,
            range=f"'{TAB_FINAL}'",
        ).execute()
    except Exception as exc:
        return f"Nettoyage OK ({nb_final} contacts) mais vidage de l'onglet impossible : {exc}"

    # Écrire en-tête + contacts nettoyés depuis A1
    values = [COLONNES] + [
        [contact.get(col, "") for col in COLONNES] for contact in contacts
    ]
    try:
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID_PRINCIPAL,
            range=f"'{TAB_FINAL}'!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
    except Exception as exc:
        return f"Onglet '{TAB_FINAL}' vidé mais écriture des données impossible : {exc}"

    return (
        f"Nettoyage terminé.\n"
        f"  Contacts bruts lus        : {nb_initial}\n"
        f"  Supprimés (A verifier=1)  : {nb_initial - nb_apres_averifier}\n"
        f"  Supprimés (liste exclusion): {nb_apres_averifier - nb_apres_exclusion}\n"
        f"  Supprimés (doublons)      : {nb_apres_exclusion - nb_final}\n"
        f"  Contacts dans le FINAL    : {nb_final}\n"
        f"  Onglet mis à jour         : '{TAB_FINAL}' dans ListeContacts_Lin_Out"
    )


@tool("Nettoyer les contacts et créer le fichier Excel FINAL dans Google Drive")
def creer_excel_nettoye_dans_drive(
    contacts_json: str,
    exclusions_json: str,
    dest_folder_id: str,
) -> str:
    """
    Reçoit les contacts bruts (JSON array) et la liste d'exclusion (JSON array d'emails),
    applique trois passes de nettoyage en mémoire :
      1. Supprime les lignes dont 'A verifier' == '1'
      2. Supprime les lignes dont l'Email figure dans la liste d'exclusion
      3. Dédoublonne sur la colonne 'Email' (première occurrence conservée)
    Crée ensuite un fichier Excel nommé ListeContacts_Lin_Out_FINAL_jjmmaaaa.xlsx
    et l'uploade dans le dossier Drive dest_folder_id (ListeFinale).
    Retourne un rapport détaillé.
    """
    return _creer_excel_nettoye_dans_drive(contacts_json, exclusions_json, dest_folder_id)
