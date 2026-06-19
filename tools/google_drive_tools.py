import csv
import io
import json
import os
import re
from datetime import datetime
from crewai.tools import tool
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


@tool("Lire un fichier CSV depuis Google Drive")
def lire_csv_depuis_drive(folder_id: str, filename: str) -> str:
    """
    Télécharge un fichier CSV depuis un dossier Google Drive et retourne
    son contenu sous forme de texte brut.
    """
    service = _get_drive_service()

    results = service.files().list(
        q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
        fields="files(id, name)",
    ).execute()

    files = results.get("files", [])
    if not files:
        return f"Aucun fichier '{filename}' trouvé dans le dossier {folder_id}."

    file_id = files[0]["id"]
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    content = buffer.getvalue().decode("utf-8", errors="ignore")
    return content


_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?!\w)')

# TLDs reconnus pour valider les emails extraits du contenu des messages LinkedIn.
# Limite les faux positifs issus du texte collé au TLD (ex: "@ifsttar.frbien").
_TLDS_VALIDES = {
    "fr", "com", "net", "org", "edu", "gov", "int", "mil", "eu",
    "de", "uk", "es", "it", "be", "nl", "ch", "at", "pl", "pt",
    "us", "ca", "au", "nz", "jp", "cn", "in", "br", "ar", "ru", "za",
    "io", "co", "me", "tv", "ac", "am", "re", "nc", "gp", "mq",
    "info", "biz", "pro", "name", "mobi", "coop", "aero",
}


def _email_tld_valide(email: str) -> bool:
    """Retourne True si le TLD de l'email est dans la liste blanche."""
    tld = email.rsplit(".", 1)[-1].lower()
    return tld in _TLDS_VALIDES

# URL LinkedIn du propriétaire du compte — exclu des contacts extraits
_OWNER_URL = "https://www.linkedin.com/in/pierre-bono-11a47328"
_SKIP_NAMES = {"LinkedIn Member", ""}


def _parse_prenom_nom(full_name: str) -> tuple[str, str]:
    """
    Découpe un nom complet LinkedIn en (Prenom, Nom).
    LinkedIn écrit souvent : 'Jean DUPONT' ou 'Soufiane EL MOUSSAOUI'.
    Les mots entièrement en majuscules (≥2 lettres) forment le Nom.
    Si aucun mot en majuscules n'est trouvé, le dernier mot devient le Nom.
    """
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0].upper()

    nom_words, prenom_words = [], []
    for word in parts:
        alpha = word.replace("-", "")
        if nom_words or (alpha.isupper() and alpha.isalpha() and len(alpha) > 1):
            nom_words.append(word)
        else:
            prenom_words.append(word)

    if not nom_words:          # Aucun mot en majuscules → dernier mot = Nom
        prenom_words, nom_words = parts[:-1], [parts[-1]]

    return " ".join(prenom_words).title(), " ".join(nom_words).upper()


def _extraire_domaine(email: str) -> tuple[str, str]:
    """Retourne (domaine, extension) depuis une adresse email."""
    try:
        domaine = email.split("@")[1].strip().lower()
        extension = "." + domaine.rsplit(".", 1)[-1]
        return domaine, extension
    except IndexError:
        return "", ""


def _extraire_contacts_connections(folder_id: str) -> str:
    """
    Logique interne : lit connections.csv depuis Drive, retourne une liste JSON de contacts.
    Appelé par le @tool homonyme et par traiter_fichier_connections dans pipeline_tools.
    """
    service = _get_drive_service()

    results = service.files().list(
        q=f"'{folder_id}' in parents and name='connections.csv' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if not files:
        return json.dumps(
            {"erreur": f"connections.csv introuvable dans le dossier {folder_id}."}
        )

    file_id = files[0]["id"]
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    content = buffer.getvalue().decode("utf-8", errors="ignore")

    # Le fichier LinkedIn connections.csv commence par des lignes de notes
    # avant la vraie ligne d'en-tête "First Name,Last Name,...".
    # On cherche cette ligne pour démarrer le parsing au bon endroit.
    lines = content.splitlines()
    header_index = next(
        (i for i, line in enumerate(lines) if line.startswith("First Name")),
        None,
    )
    if header_index is None:
        return json.dumps(
            {"erreur": "En-tête 'First Name' introuvable dans connections.csv."}
        )

    contacts = []
    reader = csv.DictReader(lines[header_index:])
    for row in reader:
        email = row.get("Email Address", "").strip()
        if not email or "@" not in email:
            continue

        prenom_raw = row.get("First Name", "").strip()
        nom_raw = row.get("Last Name", "").strip()
        domaine, extension = _extraire_domaine(email)

        contacts.append({
            "Email": email.lower(),
            "Prenom": prenom_raw.capitalize(),
            "Nom": nom_raw.upper(),
            "Source": "Linkedin",
            "A_verifier": "",
            "Domaine": domaine,
            "Statut": "",
            "Extension": extension,
        })

    return json.dumps(contacts, ensure_ascii=False, indent=2)


@tool("Extraire et formater les contacts depuis connections.csv LinkedIn")
def extraire_contacts_connections(folder_id: str) -> str:
    """
    Lit le fichier connections.csv depuis un dossier Google Drive et retourne
    une liste JSON de contacts formatés pour le Google Sheet, avec les colonnes :
    Email, Prenom (1ère lettre majuscule), Nom (MAJUSCULES), Source='Linkedin',
    A_verifier='' (vide), Domaine, Statut='' (vide), Extension.
    Seules les lignes avec une adresse email valide sont incluses.
    """
    return _extraire_contacts_connections(folder_id)


def _extraire_contacts_messages(folder_id: str) -> str:
    """
    Logique interne : lit messages.csv depuis Drive, retourne une liste JSON de contacts.
    Appelé par le @tool homonyme et par traiter_fichier_messages dans pipeline_tools.
    """
    service = _get_drive_service()

    results = service.files().list(
        q=f"'{folder_id}' in parents and name='messages.csv' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if not files:
        return json.dumps(
            {"erreur": f"messages.csv introuvable dans le dossier {folder_id}."}
        )

    file_id = files[0]["id"]
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    content_csv = buffer.getvalue().decode("utf-8", errors="ignore")

    # Le fichier LinkedIn messages.csv peut contenir des lignes de notes avant
    # la vraie ligne d'en-tête "CONVERSATION ID,...".
    # On la cherche dynamiquement, comme pour connections.csv.
    lines = content_csv.splitlines()
    header_index = next(
        (i for i, line in enumerate(lines) if "CONVERSATION ID" in line),
        None,
    )
    if header_index is None:
        return json.dumps(
            {"erreur": "En-tête 'CONVERSATION ID' introuvable dans messages.csv."}
        )

    # contacts_map : linkedin_url → {"name": str, "email": str}
    contacts_map: dict[str, dict] = {}

    reader = csv.DictReader(lines[header_index:])
    for row in reader:
        from_name = row.get("FROM", "").strip()
        from_url = row.get("SENDER PROFILE URL", "").strip()
        to_name = row.get("TO", "").strip()
        to_url = row.get("RECIPIENT PROFILE URLS", "").strip().split(",")[0].strip()
        content = row.get("CONTENT", "")

        emails_in_content = [e for e in _EMAIL_RE.findall(content) if _email_tld_valide(e)]

        # Contact FROM
        if from_name not in _SKIP_NAMES and from_url and from_url != _OWNER_URL:
            if from_url not in contacts_map:
                contacts_map[from_url] = {"name": from_name, "email": ""}
            # L'expéditeur a écrit le message → son email a plus de chances d'y figurer
            if emails_in_content and not contacts_map[from_url]["email"]:
                contacts_map[from_url]["email"] = emails_in_content[0].lower()

        # Contact TO
        if to_name not in _SKIP_NAMES and to_url and to_url != _OWNER_URL:
            if to_url not in contacts_map:
                contacts_map[to_url] = {"name": to_name, "email": ""}

    # Formater les contacts pour le Google Sheet
    # Règle : toute ligne sans email est exclue (Email est obligatoire)
    contacts = []
    for _, data in contacts_map.items():
        email = data["email"]
        if not email or "@" not in email:
            continue

        prenom, nom = _parse_prenom_nom(data["name"])
        domaine, extension = _extraire_domaine(email)

        contacts.append({
            "Email": email,
            "Prenom": prenom,
            "Nom": nom,
            "Source": "Linkedin",
            "A_verifier": "",
            "Domaine": domaine,
            "Statut": "",
            "Extension": extension,
        })

    return json.dumps(contacts, ensure_ascii=False, indent=2)


@tool("Extraire et formater les contacts depuis messages.csv LinkedIn")
def extraire_contacts_messages(folder_id: str) -> str:
    """
    Lit le fichier messages.csv depuis un dossier Google Drive et retourne
    une liste JSON de contacts formatés pour le Google Sheet, avec les colonnes :
    Email, Prenom (1ère lettre majuscule), Nom (MAJUSCULES), Source='Linkedin',
    A_verifier='' (vide), Domaine, Statut='' (vide), Extension.

    Règles d'extraction :
    - Parcourt les colonnes FROM et TO de chaque ligne.
    - Exclut le propriétaire du compte (Pierre BONO) et 'LinkedIn Member'.
    - Déduplique par URL de profil LinkedIn (clé fiable).
    - Cherche les emails dans CONTENT : si la personne est l'expéditeur (FROM)
      d'un message contenant un email, cet email lui est associé.
    - Les colonnes 'A vérifier' et 'Statut' sont laissées vides.
    """
    return _extraire_contacts_messages(folder_id)


def _archiver_fichier(
    source_folder_id: str, archives_folder_id: str, filename: str = ""
) -> str:
    """
    Logique interne : archive un ou plusieurs fichiers Drive avec la date dans le nom.
    Appelé par le @tool homonyme et par les outils pipeline de pipeline_tools.
    """
    service = _get_drive_service()
    date_str = datetime.now().strftime("%d%m%Y")

    query = (
        f"'{source_folder_id}' in parents and trashed=false "
        f"and mimeType != 'application/vnd.google-apps.folder'"
    )
    if filename:
        query += f" and name='{filename}'"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if not files:
        cible = f"'{filename}'" if filename else "fichier"
        return f"Aucun {cible} trouvé dans le dossier source {source_folder_id}."

    archives = []
    for f in files:
        if "." in f["name"]:
            base, ext = f["name"].rsplit(".", 1)
            nouveau_nom = f"{base}_{date_str}.{ext}"
        else:
            nouveau_nom = f"{f['name']}_{date_str}"

        service.files().update(
            fileId=f["id"],
            addParents=archives_folder_id,
            removeParents=source_folder_id,
            body={"name": nouveau_nom},
            fields="id, name, parents",
        ).execute()

        archives.append(f"{f['name']} → {nouveau_nom}")

    return (
        f"{len(archives)} fichier(s) archivé(s) dans le dossier Archives : "
        + ", ".join(archives) + "."
    )


@tool("Archiver un fichier Google Drive avec la date dans le nom")
def archiver_fichier_drive(
    source_folder_id: str, archives_folder_id: str, filename: str = ""
) -> str:
    """
    Trouve un ou plusieurs fichiers dans un dossier Google Drive source,
    les renomme avec la date du jour (format : nom_jjmmaaaa.ext),
    les déplace dans le dossier Archives et vide ainsi le dossier source.

    - Si filename est fourni : archive uniquement ce fichier.
    - Si filename est vide   : archive tous les fichiers du dossier source.
    - Format du nouveau nom  : ex. connections_17062026.csv
    """
    return _archiver_fichier(source_folder_id, archives_folder_id, filename)


@tool("Vérifier la présence d'un fichier dans un dossier Drive")
def verifier_fichier_dans_drive(folder_id: str, filename: str) -> str:
    """
    Vérifie si un fichier donné est présent dans un dossier Google Drive.
    Retourne 'PRESENT' ou 'ABSENT'.
    """
    service = _get_drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    return "PRESENT" if files else "ABSENT"
