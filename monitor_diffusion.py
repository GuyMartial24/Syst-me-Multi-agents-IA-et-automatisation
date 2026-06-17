"""
Surveillance continue du dossier Drive 'Diffusion_et_Communication'.
Dès qu'un nouveau fichier Excel 'ListeContacts_Lin_Out_FINAL' y est détecté,
lance automatiquement le crew de diffusion (crew_diffusion.py).

Intervalle de polling : 10 minutes.
Lancement : python monitor_diffusion.py
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

FOLDER_DIFFUSION = "1peQ9728pAY2h2j60i-Wns4-bXyjZzVzl"
POLLING_INTERVAL = 1200  # 20 minutes
STATE_FILE       = Path(__file__).parent / ".monitor_diffusion_state.json"

SCOPES = ["https://www.googleapis.com/auth/drive"]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor_diffusion.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── Google Drive ──────────────────────────────────────────────────────────────

def _get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def lister_fichiers_liste_finale(service) -> list[dict]:
    """
    Retourne les fichiers nommés 'ListeContacts_Lin_Out_FINAL*' dans le dossier
    Diffusion_et_Communication (non supprimés).
    Chaque entrée : {"id": "...", "name": "..."}.
    """
    results = service.files().list(
        q=(
            f"'{FOLDER_DIFFUSION}' in parents "
            "and name contains 'ListeContacts_Lin_Out_FINAL' "
            "and trashed=false"
        ),
        fields="files(id, name)",
    ).execute()
    return results.get("files", [])


# ── État persisté ─────────────────────────────────────────────────────────────

def charger_ids_traites() -> set[str]:
    """Charge les IDs de fichiers déjà traités depuis le fichier JSON local."""
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def sauvegarder_ids_traites(ids: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(ids)), encoding="utf-8")


# ── Cycle de surveillance ─────────────────────────────────────────────────────

def run_cycle() -> None:
    try:
        service       = _get_drive_service()
        fichiers      = lister_fichiers_liste_finale(service)
        ids_traites   = charger_ids_traites()

        nouveaux = [f for f in fichiers if f["id"] not in ids_traites]

        if not nouveaux:
            log.info(
                f"Aucun nouveau fichier 'ListeContacts_Lin_Out_FINAL' détecté "
                f"({len(fichiers)} fichier(s) déjà traité(s))."
            )
            return

        for fichier in nouveaux:
            log.info(
                f"Nouveau fichier détecté : {fichier['name']} (id={fichier['id']}). "
                "Lancement du crew de diffusion…"
            )
            try:
                from crew_diffusion import run_diffusion
                rapport = run_diffusion()
                log.info(f"Diffusion terminée.\n{rapport}")
                ids_traites.add(fichier["id"])
                sauvegarder_ids_traites(ids_traites)
            except Exception as exc:
                log.error(
                    f"Erreur lors de la diffusion pour {fichier['name']} : {exc}",
                    exc_info=True,
                )

    except Exception as exc:
        log.error(f"Erreur lors du cycle de surveillance : {exc}", exc_info=True)


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("Démarrage du moniteur Diffusion_et_Com (intervalle : 20 min)")
    log.info(f"Dossier surveillé : {FOLDER_DIFFUSION}")
    log.info("=" * 60)

    run_cycle()

    try:
        while True:
            log.info(f"Prochain cycle dans {POLLING_INTERVAL // 60} min…")
            time.sleep(POLLING_INTERVAL)
            run_cycle()
    except KeyboardInterrupt:
        log.info("Arrêt du moniteur (Ctrl+C).")
