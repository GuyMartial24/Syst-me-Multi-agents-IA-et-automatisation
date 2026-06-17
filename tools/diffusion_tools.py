import io
import json
import os
import requests
from crewai.tools import tool
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive"]
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# ID fixe du fichier ContenuMessage.docx dans Diffusion_et_Communication
CONTENU_MESSAGE_FILE_ID = "14V2EpnEaO4EW4AHKmNGM6w2An-GWrYhn"


def _get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _download_bytes(service, file_id: str) -> bytes:
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def _extraire_objet_et_corps(texte: str) -> tuple[str, str]:
    """
    Extrait l'objet et le corps depuis le texte brut de ContenuMessage.
    Convention attendue :
        Objet: [ligne contenant l'objet de l'email]
        [ligne vide optionnelle]
        [corps du message]

    Si aucune ligne "Objet:" n'est trouvée, la première ligne devient l'objet.
    """
    lines = texte.splitlines()
    objet = ""
    corps_lines = []
    objet_trouve = False

    for i, line in enumerate(lines):
        if not objet_trouve and line.strip().lower().startswith("objet:"):
            objet = line.split(":", 1)[1].strip()
            objet_trouve = True
            # le corps commence après la ligne Objet (et une éventuelle ligne vide)
            corps_lines = [l for l in lines[i + 1:] if l.strip() or corps_lines]
            break

    if not objet_trouve:
        # Pas de ligne "Objet:" → première ligne = objet, reste = corps
        objet = lines[0].strip() if lines else ""
        corps_lines = lines[1:]

    corps = "\n".join(corps_lines).strip()
    return objet, corps


@tool("Lire le fichier ContenuMessage depuis Google Drive")
def lire_contenu_message_depuis_drive() -> str:
    """
    Lit le fichier ContenuMessage.docx depuis Google Drive (ID fixe, format .docx uniquement).
    Retourne un JSON {"objet": "...", "corps": "..."} extrait selon la convention :
      - La ligne commençant par 'Objet:' contient le sujet de l'email.
      - Le reste du fichier constitue le corps du message.
    """
    service = _get_drive_service()
    meta = service.files().get(
        fileId=CONTENU_MESSAGE_FILE_ID, fields="name"
    ).execute()
    name = meta["name"].lower()
    data = _download_bytes(service, CONTENU_MESSAGE_FILE_ID)

    if name.endswith(".txt"):
        texte = data.decode("utf-8", errors="ignore").strip()

    elif name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(data))
        texte = "\n".join(p.text for p in doc.paragraphs)

    elif name.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            texte = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()

    else:
        return json.dumps({
            "erreur": f"Format non supporté ({meta['name']}). Utiliser .txt, .docx ou .pdf."
        })

    objet, corps = _extraire_objet_et_corps(texte)
    return json.dumps({"objet": objet, "corps": corps}, ensure_ascii=False)


@tool("Lire les emails depuis le fichier Excel ListeContacts_Lin_Out_FINAL")
def lire_emails_depuis_excel_drive(folder_id: str) -> str:
    """
    Lit le fichier Excel 'ListeContacts_Lin_Out_FINAL.xlsx' dans le dossier
    Google Drive spécifié et retourne la liste JSON des adresses email
    (colonne 'Email', lignes sans email ignorées).
    """
    service = _get_drive_service()

    results = service.files().list(
        q=(
            f"'{folder_id}' in parents "
            "and name contains 'ListeContacts_Lin_Out_FINAL' "
            "and trashed=false"
        ),
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if not files:
        return json.dumps({"erreur": "Fichier ListeContacts_Lin_Out_FINAL introuvable."})

    data = _download_bytes(service, files[0]["id"])

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data))
    ws = wb.active

    headers = [cell.value for cell in ws[1]]
    try:
        col_email = headers.index("Email")
    except ValueError:
        return json.dumps({"erreur": "Colonne 'Email' introuvable dans le fichier Excel."})

    emails = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        val = row[col_email] if len(row) > col_email else None
        if val and "@" in str(val):
            emails.append(str(val).strip().lower())

    return json.dumps(emails, ensure_ascii=False)


@tool("Envoyer un message identique à une liste d'emails via Sendinblue (Brevo)")
def envoyer_emails_via_sendinblue(emails_json: str, sujet: str, contenu: str) -> str:
    """
    Envoie un email identique à chaque adresse de emails_json via l'API Brevo (Sendinblue).
    - emails_json : JSON array de chaînes email
    - sujet       : objet de l'email (extrait de ContenuMessage)
    - contenu     : corps du message en texte brut (extrait de ContenuMessage)

    Variables d'environnement requises :
      SENDINBLUE_API_KEY      — clé API Brevo
      SENDINBLUE_SENDER_EMAIL — adresse expéditeur
      SENDINBLUE_SENDER_NAME  — nom affiché de l'expéditeur
    """
    api_key      = os.environ.get("SENDINBLUE_API_KEY", "")
    sender_email = os.environ.get("SENDINBLUE_SENDER_EMAIL", "")
    sender_name  = os.environ.get("SENDINBLUE_SENDER_NAME", "")

    if not api_key:
        return "ERREUR : variable SENDINBLUE_API_KEY non configurée."
    if not sender_email:
        return "ERREUR : variable SENDINBLUE_SENDER_EMAIL non configurée."

    emails = json.loads(emails_json)
    if isinstance(emails, dict) and "erreur" in emails:
        return f"ERREUR lors de la lecture des emails : {emails['erreur']}"
    if not emails:
        return "Aucune adresse email à contacter."

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    nb_ok, nb_err, erreurs = 0, 0, []

    for email in emails:
        payload = {
            "sender": {"name": sender_name, "email": sender_email},
            "to": [{"email": email}],
            "subject": sujet,
            "textContent": contenu,
        }
        try:
            resp = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code in (200, 201):
                nb_ok += 1
            else:
                nb_err += 1
                erreurs.append(f"{email} → HTTP {resp.status_code}: {resp.text[:120]}")
        except requests.RequestException as exc:
            nb_err += 1
            erreurs.append(f"{email} → Exception: {exc}")

    rapport = (
        f"Diffusion terminée : {nb_ok} email(s) envoyé(s) avec succès, "
        f"{nb_err} échec(s)."
    )
    if erreurs:
        rapport += "\nDétail des échecs :\n" + "\n".join(erreurs)
    return rapport
