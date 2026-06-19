"""
Monitor principal — surveille les triggers des 4 agents d'extraction et nettoyage.

Triggers surveillés :
  Agent 1 (Connections) : présence de connections.csv dans FOLDER_LINKEDIN_CONNECTIONS
  Agent 2 (Messages)    : présence de messages.csv dans FOLDER_LINKEDIN_MESSAGES
  Agent 3 (Outlook)     : nouveaux emails dans inbox/sentItems via Microsoft Graph API
                          (polling par timestamp — $filter=receivedDateTime gt {last_check})
  Agent 4 (Nettoyeur)   : présence de tout fichier dans FOLDER_LISTE_BRUTE

Intervalles de polling :
  Connections : 6 minutes
  Messages    : 8 minutes
  Outlook     : 5 minutes
  Nettoyeur   : 15 minutes

Lancement : python monitor_main.py
Arrêt      : Ctrl+C
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

# ── Constantes ────────────────────────────────────────────────────────────────

FOLDER_LINKEDIN_CONNECTIONS = "1X_IDqTFPg-Hh-jkRnyTBnDjVmaXtgF_1"
FOLDER_LINKEDIN_MESSAGES = "1Qd9yDA2N4kHSovlGA8aZavlAbQ3yeI2b"
FOLDER_LISTE_BRUTE = "1JCQvWRjGHH01wzgQDhVK9ho57xszIlI4"

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

INTERVALS = {
    "connections":  6 * 60,   #  6 min
    "messages":     8 * 60,   #  8 min
    "outlook":      5 * 60,   #  5 min
    "nettoyeur":   15 * 60,   # 15 min
}

STATE_FILE = Path(__file__).parent.parent / ".monitor_main_state.json"
SCOPES_DRIVE = ["https://www.googleapis.com/auth/drive"]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor_main.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── État persisté ─────────────────────────────────────────────────────────────

def charger_etat() -> dict:
    """
    Structure du state :
    {
      "last_check": {                 # timestamp Unix du dernier cycle par trigger
          "connections": 0,
          "messages": 0,
          "outlook": 0,
          "nettoyeur": 0
      },
      "outlook_last_dt": "",          # ISO 8601 UTC du dernier message traité
      "fichiers_traites": {           # IDs Drive déjà traités par trigger
          "connections": [],
          "messages": [],
          "nettoyeur": []
      }
    }
    """
    defaults = {
        "last_check": {k: 0 for k in INTERVALS},
        "outlook_last_dt": "",
        "fichiers_traites": {"connections": [], "messages": [], "nettoyeur": []},
    }
    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            # Fusion profonde : les valeurs sauvegardées écrasent les defaults
            if isinstance(saved.get("last_check"), dict):
                defaults["last_check"].update(saved["last_check"])
            if "outlook_last_dt" in saved:
                defaults["outlook_last_dt"] = saved["outlook_last_dt"]
            if isinstance(saved.get("fichiers_traites"), dict):
                for k in defaults["fichiers_traites"]:
                    if k in saved["fichiers_traites"]:
                        defaults["fichiers_traites"][k] = saved["fichiers_traites"][k]
        except Exception:
            pass
    return defaults


def sauvegarder_etat(etat: dict) -> None:
    STATE_FILE.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")


# ── Google Drive ──────────────────────────────────────────────────────────────

def _get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"], scopes=SCOPES_DRIVE
    )
    return build("drive", "v3", credentials=creds)


def _lister_fichiers(service, folder_id: str, name_filter: str = "") -> list[dict]:
    """Liste les fichiers non supprimés d'un dossier Drive (filtre nom optionnel)."""
    q = (
        f"'{folder_id}' in parents and trashed=false "
        "and mimeType != 'application/vnd.google-apps.folder'"
    )
    if name_filter:
        q += f" and name='{name_filter}'"
    results = service.files().list(q=q, fields="files(id, name)").execute()
    return results.get("files", [])


# ── Microsoft Graph API — polling Outlook ────────────────────────────────────

def _get_graph_token() -> str:
    tenant_id = os.environ["OUTLOOK_OAUTH_TENANT_ID"]
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": os.environ["OUTLOOK_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["OUTLOOK_OAUTH_CLIENT_SECRET"],
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    resp = requests.post(url, data=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _compter_nouveaux_emails(token: str, mailbox: str, since_iso: str) -> int:
    """
    Compte les messages reçus/envoyés après since_iso (format ISO 8601 UTC).
    Utilise $filter=receivedDateTime gt {since_iso} pour inbox,
    et $filter=sentDateTime gt {since_iso} pour sentItems.
    Retourne le nombre total de nouveaux messages.
    """
    headers = {"Authorization": f"Bearer {token}"}
    total = 0

    for folder, field in [("inbox", "receivedDateTime"), ("sentItems", "sentDateTime")]:
        url = (
            f"{GRAPH_API_BASE}/users/{mailbox}/mailFolders/{folder}/messages"
            f"?$filter={field} gt {since_iso}"
            f"&$select=id&$top=50"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            total += len(resp.json().get("value", []))
        except Exception as exc:
            log.warning(f"Erreur lecture {folder} Outlook : {exc}")

    return total


# ── Runners des crews ─────────────────────────────────────────────────────────

def _lancer_crew(nom: str, runner_fn) -> None:
    log.info(f"Déclenchement du crew : {nom}…")
    try:
        rapport = runner_fn()
        # Tronquer à 3 lignes : le LLM ajoute des contacts inventés après la sortie réelle de l'outil
        lignes = str(rapport).splitlines()
        log.info(f"Crew '{nom}' terminé.\n" + "\n".join(lignes[:3]))
    except Exception as exc:
        log.error(f"Erreur crew '{nom}' : {exc}", exc_info=True)


# ── Cycles de vérification par trigger ───────────────────────────────────────

def check_connections(etat: dict) -> None:
    log.info("[Connections] Vérification…")
    try:
        service = _get_drive_service()
        fichiers = _lister_fichiers(service, FOLDER_LINKEDIN_CONNECTIONS, "connections.csv")
    except Exception as exc:
        log.error(f"[Connections] Erreur accès Drive : {exc}", exc_info=True)
        return
    traites = set(etat["fichiers_traites"]["connections"])
    nouveaux = [f for f in fichiers if f["id"] not in traites]

    if not nouveaux:
        log.info("[Connections] Aucun nouveau fichier connections.csv.")
        return

    log.info(f"[Connections] {len(nouveaux)} fichier(s) détecté(s).")
    from crews.crew_connections import run_connections
    _lancer_crew("Extracteur Connections", run_connections)
    # Marquer traités même si le crew a échoué (évite la boucle infinie)
    for f in nouveaux:
        traites.add(f["id"])
    etat["fichiers_traites"]["connections"] = list(traites)


def check_messages(etat: dict) -> None:
    log.info("[Messages] Vérification…")
    try:
        service = _get_drive_service()
        fichiers = _lister_fichiers(service, FOLDER_LINKEDIN_MESSAGES, "messages.csv")
    except Exception as exc:
        log.error(f"[Messages] Erreur accès Drive : {exc}", exc_info=True)
        return
    traites = set(etat["fichiers_traites"]["messages"])
    nouveaux = [f for f in fichiers if f["id"] not in traites]

    if not nouveaux:
        log.info("[Messages] Aucun nouveau fichier messages.csv.")
        return

    log.info(f"[Messages] {len(nouveaux)} fichier(s) détecté(s).")
    from crews.crew_messages import run_messages
    _lancer_crew("Extracteur Messages", run_messages)

    for f in nouveaux:
        traites.add(f["id"])
    etat["fichiers_traites"]["messages"] = list(traites)


def check_outlook(etat: dict) -> None:
    log.info("[Outlook] Vérification des nouveaux emails…")

    # Si premier passage : initialiser le timestamp à maintenant (ne pas retraiter l'historique)
    if not etat["outlook_last_dt"]:
        etat["outlook_last_dt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log.info(f"[Outlook] Initialisation du timestamp à {etat['outlook_last_dt']}.")
        return

    try:
        token = _get_graph_token()
        mailbox = os.environ["OUTLOOK_TARGET_MAILBOX"]
        nb_new = _compter_nouveaux_emails(token, mailbox, etat["outlook_last_dt"])
    except Exception as exc:
        log.error(f"[Outlook] Erreur d'accès à Graph API : {exc}", exc_info=True)
        return

    if nb_new == 0:
        log.info(f"[Outlook] Aucun nouveau message depuis {etat['outlook_last_dt']}.")
        return

    log.info(f"[Outlook] {nb_new} nouveau(x) message(s) détecté(s).")

    # Injecter le timestamp dans l'env pour que lire_emails_outlook filtre correctement
    os.environ["OUTLOOK_SINCE_DT"] = etat["outlook_last_dt"]
    from crews.crew_outlook import run_outlook
    _lancer_crew("Extracteur Outlook", run_outlook)
    os.environ.pop("OUTLOOK_SINCE_DT", None)  # nettoyer après usage

    # Mettre à jour le timestamp APRÈS le traitement réussi
    etat["outlook_last_dt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_nettoyeur(etat: dict) -> None:
    log.info("[Nettoyeur] Vérification du dossier ListeContacts_Lin_Out_brute…")
    try:
        service = _get_drive_service()
        fichiers = _lister_fichiers(service, FOLDER_LISTE_BRUTE)
    except Exception as exc:
        log.error(f"[Nettoyeur] Erreur accès Drive : {exc}", exc_info=True)
        return
    # Filtrer uniquement les fichiers nommés "ListeContacts_Lin_Out" (avec ou sans .xlsx)
    fichiers = [
        f for f in fichiers
        if f["name"].startswith("ListeContacts_Lin_Out")
        and not f["name"].startswith("ListeContacts_Lin_Out_FINAL")
    ]
    traites = set(etat["fichiers_traites"]["nettoyeur"])
    nouveaux = [f for f in fichiers if f["id"] not in traites]

    if not nouveaux:
        log.info("[Nettoyeur] Dossier vide — aucun fichier déclencheur.")
        return

    noms = ", ".join(f["name"] for f in nouveaux)
    log.info(f"[Nettoyeur] Fichier(s) détecté(s) : {noms}.")
    from crews.crew_nettoyeur import run_nettoyeur
    _lancer_crew("Nettoyeur", run_nettoyeur)

    for f in nouveaux:
        traites.add(f["id"])
    etat["fichiers_traites"]["nettoyeur"] = list(traites)


# ── Boucle principale ─────────────────────────────────────────────────────────

CHECKS = {
    "connections": check_connections,
    "messages": check_messages,
    "outlook": check_outlook,
    "nettoyeur": check_nettoyeur,
}

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("Démarrage de monitor_main.py")
    log.info("Triggers : Connections(6min) | Messages(8min) | Outlook(5min) | Nettoyeur(15min)")
    log.info("=" * 60)

    etat = charger_etat()

    # Premier cycle immédiat au démarrage (sauf Outlook qui initialise son timestamp)
    for nom, fn in CHECKS.items():
        fn(etat)
        etat["last_check"][nom] = time.time()
    sauvegarder_etat(etat)

    try:
        while True:
            time.sleep(60)  # vérifie chaque minute si un trigger est dû
            now = time.time()
            etat = charger_etat()

            for nom, interval in INTERVALS.items():
                if now - etat["last_check"].get(nom, 0) >= interval:
                    CHECKS[nom](etat)
                    etat["last_check"][nom] = now
                    sauvegarder_etat(etat)

    except KeyboardInterrupt:
        log.info("Arrêt de monitor_main.py (Ctrl+C).")
