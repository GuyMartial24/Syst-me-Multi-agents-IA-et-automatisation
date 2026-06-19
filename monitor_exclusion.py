"""
Surveillance continue de ListeExclusion → nettoyage de ListeContacts_Lin_Out.

Fonctionnement :
  - Toutes les 10 minutes, lit la colonne "Email exclu" du Google Sheet ListeExclusion.
  - Compare avec l'état précédent (persisté dans .monitor_state.json).
  - Si de nouvelles adresses sont détectées, les supprime immédiatement de
    l'onglet ListeContacts_Lin_Out dans le Google Sheet principal.
  - Journalise chaque action dans monitor_exclusion.log.

Lancement : python monitor_exclusion.py
Arrêt      : Ctrl+C
"""

import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

# ── Constantes ────────────────────────────────────────────────────────────────

SHEET_ID_EXCLUSION = "1sz7xUM05y6xI-bj1Wz8jvmOzuIH7ZzCoEyECgqkZ9xc"
SHEET_ID_FINALE = "1yEWVIlazcfih3iymhICk3pY2jXwVAisgeZB8WVje8a0"
TAB_FINALE = "ListeContacts_Lin_Out"
COLONNE_EMAIL = "Email"

POLLING_INTERVAL = 600  # secondes (10 minutes)
STATE_FILE = Path(__file__).parent / ".monitor_state.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor_exclusion.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── Google Sheets ─────────────────────────────────────────────────────────────

def _get_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def lire_emails_exclusion(service) -> set[str]:
    """Retourne l'ensemble des emails de ListeExclusion (colonne A, sans en-tête)."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID_EXCLUSION,
        range="A:A",
    ).execute()
    rows = result.get("values", [])
    emails: set[str] = set()
    for row in rows[1:]:  # ligne 0 = en-tête "Emails exclus"
        if row and row[0].strip():
            emails.add(row[0].strip().lower())
    return emails


def supprimer_de_finale(service, emails_a_supprimer: set[str]) -> int:
    """
    Supprime de TAB_FINALE les lignes dont l'email est dans emails_a_supprimer.
    Retourne le nombre de lignes supprimées.
    """
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID_FINALE,
        range=TAB_FINALE,
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return 0

    headers = rows[0]
    try:
        col_idx = headers.index(COLONNE_EMAIL)
    except ValueError:
        log.error(f"Colonne '{COLONNE_EMAIL}' introuvable dans l'onglet '{TAB_FINALE}'.")
        return 0

    conservees = [headers]
    nb_suppr = 0
    for row in rows[1:]:
        email = row[col_idx].strip().lower() if len(row) > col_idx else ""
        if email in emails_a_supprimer:
            nb_suppr += 1
            log.info(f"  → Suppression : {email}")
        else:
            conservees.append(row)

    if nb_suppr > 0:
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID_FINALE,
            range=f"{TAB_FINALE}!A1",
            valueInputOption="RAW",
            body={"values": conservees},
        ).execute()

    return nb_suppr


# ── État persisté ─────────────────────────────────────────────────────────────

def charger_etat() -> set[str]:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def sauvegarder_etat(emails: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(emails)), encoding="utf-8")


# ── Cycle de surveillance ─────────────────────────────────────────────────────

def run_cycle() -> None:
    try:
        service = _get_service()

        emails_actuels = lire_emails_exclusion(service)
        emails_connus = charger_etat()
        nouveaux = emails_actuels - emails_connus

        if not nouveaux:
            log.info(
                f"Aucune nouvelle adresse dans ListeExclusion "
                f"({len(emails_actuels)} entrée(s) connue(s))."
            )
            return

        log.info(
            f"{len(nouveaux)} nouvelle(s) adresse(s) détectée(s) dans ListeExclusion : "
            + ", ".join(sorted(nouveaux))
        )

        nb = supprimer_de_finale(service, nouveaux)

        if nb > 0:
            log.info(f"{nb} ligne(s) supprimée(s) de '{TAB_FINALE}'.")
        else:
            log.info(f"Aucune ligne correspondante trouvée dans '{TAB_FINALE}'.")

        # Mettre à jour l'état connu même si 0 ligne supprimée
        # (évite de re-tenter indéfiniment pour un email absent de la liste finale)
        sauvegarder_etat(emails_actuels)

    except Exception as exc:
        log.error(f"Erreur lors du cycle de surveillance : {exc}", exc_info=True)


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("Démarrage du moniteur ListeExclusion (intervalle : 10 min)")
    log.info(f"Suppression des exclusions dans l'onglet : {TAB_FINALE}")
    log.info("=" * 60)

    # Premier cycle immédiat au démarrage
    run_cycle()

    try:
        while True:
            log.info(f"Prochain cycle dans {POLLING_INTERVAL // 60} minutes…")
            time.sleep(POLLING_INTERVAL)
            run_cycle()
    except KeyboardInterrupt:
        log.info("Arrêt du moniteur (Ctrl+C).")
