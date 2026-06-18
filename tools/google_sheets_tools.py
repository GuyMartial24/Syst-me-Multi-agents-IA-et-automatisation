import json
import os
from datetime import datetime
from crewai.tools import tool
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_ID = "1yEWVIlazcfih3iymhICk3pY2jXwVAisgeZB8WVje8a0"

# Ordre fixe des colonnes correspondant exactement au Google Sheet (A → I)
COLONNES_SHEET = [
    "Email",           # A
    "Prenom",          # B
    "Nom",             # C
    "Source",          # D
    "A_verifier",      # E
    "Domaine",         # F
    "Statut",          # G
    "Extension",       # H
    "Date_insertion",  # I — timestamp ajouté automatiquement à l'écriture
]


def _get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


@tool("Lire un onglet du Google Sheet")
def lire_google_sheet(tab_name: str) -> str:
    """
    Lit le contenu d'un onglet du Google Sheet principal et le retourne en JSON.
    """
    service = _get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=tab_name,
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return "[]"
    headers = rows[0]
    data = [dict(zip(headers, row)) for row in rows[1:]]
    return json.dumps(data, ensure_ascii=False, indent=2)


@tool("Écrire des données dans un onglet du Google Sheet")
def ecrire_dans_google_sheet(tab_name: str, rows_json: str) -> str:
    """
    Écrit une liste de lignes JSON dans un onglet du Google Sheet.
    rows_json : JSON array d'objets avec les mêmes clés que les colonnes.
    """
    service = _get_sheets_service()
    rows = json.loads(rows_json)
    if not rows:
        return "Aucune donnée à écrire."

    headers = list(rows[0].keys())
    values = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows]

    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()

    return f"{len(rows)} lignes écrites dans l'onglet '{tab_name}'."


@tool("Écrire des contacts dans le Google Sheet en évitant les doublons")
def ecrire_contacts_sans_doublons(tab_name: str, rows_json: str) -> str:
    """
    Insère une liste de contacts (JSON array) dans un onglet du Google Sheet
    en vérifiant les doublons sur la colonne 'Email' (insensible à la casse).
    - Si un email existe déjà dans l'onglet, la ligne est ignorée (version existante conservée).
    - Seuls les nouveaux contacts sont ajoutés à la fin de l'onglet.
    - Retourne un rapport : nombre ajoutés / ignorés.
    """
    service = _get_sheets_service()
    tous = json.loads(rows_json)
    if not tous:
        return "Aucune donnée à écrire."

    # Règle absolue : toute ligne sans Email est rejetée avant toute opération
    nouveaux = [r for r in tous if r.get("Email", "").strip()]
    nb_sans_email = len(tous) - len(nouveaux)
    if not nouveaux:
        return f"0 contact inséré. {nb_sans_email} rejeté(s) : colonne Email vide (obligatoire)."

    # Lire les données existantes dans l'onglet
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=tab_name,
    ).execute()
    existing_rows = result.get("values", [])

    # Construire l'ensemble des emails déjà présents dans l'onglet
    emails_existants: set[str] = set()
    if existing_rows and len(existing_rows) > 1:
        try:
            col_email = existing_rows[0].index("Email")
            for row in existing_rows[1:]:
                email = row[col_email].strip().lower() if len(row) > col_email else ""
                if email:
                    emails_existants.add(email)
        except ValueError:
            pass  # Colonne Email absente → on insère tout

    # Filtrer : ne garder que les contacts dont l'email n'est pas déjà présent
    headers = list(nouveaux[0].keys())
    a_inserer = []
    nb_ignores = 0
    for contact in nouveaux:
        email = contact.get("Email", "").strip().lower()
        if email in emails_existants:
            nb_ignores += 1
        else:
            a_inserer.append(contact)
            emails_existants.add(email)  # évite les doublons dans le lot entrant

    nb_ajoutes = len(a_inserer)

    # Ajouter le timestamp d'insertion à chaque nouveau contact (format jj/mm/aa)
    date_insertion = datetime.now().strftime("%d/%m/%Y")
    for contact in a_inserer:
        contact["Date_insertion"] = date_insertion

    if not existing_rows:
        # Onglet vide : écrire l'en-tête + les données depuis A1
        values = [COLONNES_SHEET] + [[str(c.get(h, "")) for h in COLONNES_SHEET] for c in a_inserer]
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{tab_name}!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
    elif a_inserer:
        # Onglet existant : ajouter uniquement les nouvelles lignes à la fin
        values = [[str(c.get(h, "")) for h in COLONNES_SHEET] for c in a_inserer]
        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"{tab_name}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()

    rapport = (
        f"{nb_ajoutes} contact(s) ajouté(s) dans '{tab_name}'. "
        f"{nb_ignores} ignoré(s) car déjà présent(s) (version existante conservée)."
    )
    if nb_sans_email:
        rapport += f" {nb_sans_email} rejeté(s) : Email vide (obligatoire)."
    return rapport


@tool("Supprimer les lignes 'A vérifier' = 1 du Google Sheet")
def supprimer_lignes_a_verifier(tab_name: str) -> str:
    """
    Supprime toutes les lignes dont la colonne 'A vérifier' vaut 1
    dans l'onglet spécifié du Google Sheet.
    """
    import json
    service = _get_sheets_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=tab_name,
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return "Onglet vide."

    headers = rows[0]
    # Recherche insensible à la casse et aux variantes (A_verifier / A vérifier)
    col_idx = next(
        (i for i, h in enumerate(headers) if h.replace(" ", "_").lower() == "a_verifier"),
        None,
    )
    if col_idx is None:
        return "Colonne 'A_verifier' introuvable dans l'onglet."

    lignes_filtrees = [headers] + [
        row for row in rows[1:]
        if len(row) <= col_idx or str(row[col_idx]).strip() != "1"
    ]
    nb_supprimees = len(rows) - len(lignes_filtrees)

    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        body={"values": lignes_filtrees},
    ).execute()

    return f"{nb_supprimees} lignes supprimées. {len(lignes_filtrees) - 1} lignes conservées."


SHEET_ID_EXCLUSION = "1sz7xUM05y6xI-bj1Wz8jvmOzuIH7ZzCoEyECgqkZ9xc"


@tool("Supprimer les emails exclus du Google Sheet")
def supprimer_emails_exclus(tab_name: str) -> str:
    """
    Lit la colonne 'Emails exclus' du Google Sheet ListeExclusion
    (ID fixe : 1sz7xUM05y6xI-bj1Wz8jvmOzuIH7ZzCoEyECgqkZ9xc)
    puis supprime de l'onglet tab_name du Google Sheet principal
    toutes les lignes dont l'email figure dans cette liste d'exclusion.
    """
    service = _get_sheets_service()

    # Lire la liste d'exclusion (colonne A, en-tête "Emails exclus")
    result_excl = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID_EXCLUSION,
        range="A:A",
    ).execute()
    rows_excl = result_excl.get("values", [])

    emails_exclus: set[str] = set()
    for row in rows_excl[1:]:  # ligne 0 = en-tête "Emails exclus"
        if row and row[0].strip():
            emails_exclus.add(row[0].strip().lower())

    if not emails_exclus:
        return "ListeExclusion vide — aucun email à exclure."

    # Lire l'onglet cible dans le Google Sheet principal
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=tab_name,
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return f"Onglet '{tab_name}' vide."

    headers = rows[0]
    try:
        col_email = headers.index("Email")
    except ValueError:
        return "Colonne 'Email' introuvable dans l'onglet cible."

    lignes_conservees = [headers]
    nb_supprimees = 0
    for row in rows[1:]:
        email = row[col_email].strip().lower() if len(row) > col_email else ""
        if email in emails_exclus:
            nb_supprimees += 1
        else:
            lignes_conservees.append(row)

    if nb_supprimees > 0:
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{tab_name}!A1",
            valueInputOption="RAW",
            body={"values": lignes_conservees},
        ).execute()

    return (
        f"{nb_supprimees} ligne(s) supprimée(s) (emails présents dans ListeExclusion). "
        f"{len(lignes_conservees) - 1} ligne(s) conservée(s) dans '{tab_name}'."
    )


@tool("Dédoublonner un onglet du Google Sheet")
def dedoublonner_google_sheet(tab_name: str, cle_dedup: str = "Email") -> str:
    """
    Supprime les doublons d'un onglet du Google Sheet en se basant
    sur la colonne spécifiée (par défaut : 'Email'). Recherche insensible à la casse.
    """
    service = _get_sheets_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=tab_name,
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return "Onglet vide."

    headers = rows[0]
    col_idx = next(
        (i for i, h in enumerate(headers) if h.lower() == cle_dedup.lower()),
        None,
    )
    if col_idx is None:
        return f"Colonne '{cle_dedup}' introuvable."

    vus = set()
    uniques = [headers]
    for row in rows[1:]:
        val = row[col_idx].strip().lower() if len(row) > col_idx else ""
        if val and val not in vus:
            vus.add(val)
            uniques.append(row)

    nb_doublons = len(rows) - len(uniques)
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        body={"values": uniques},
    ).execute()

    return f"{nb_doublons} doublons supprimés. {len(uniques) - 1} lignes uniques conservées."
