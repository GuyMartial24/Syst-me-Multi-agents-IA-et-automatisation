"""
Diagnostic pipeline MINER — teste chaque composant indépendamment du LLM.
Lancement (depuis MINER_production/) : python test_pipeline.py
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent))

SEP = "─" * 60

# ── TEST 0 : liste des onglets du Sheet ──────────────────────────────────────

def test_sheet_tabs():
    """Liste les onglets et corrige les noms avec espaces superflus."""
    print(f"\n{SEP}")
    print("TEST 0 : Google Sheets — onglets (+ correction des espaces)")
    print(SEP)
    from tools.google_sheets_tools import _get_sheets_service, SHEET_ID
    service = _get_sheets_service()
    meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    for sheet in meta.get("sheets", []):
        props = sheet["properties"]
        title = props["title"]
        title_stripped = title.strip()
        print(f"  Onglet brut : '{title}'  (gid={props['sheetId']})")
        if title != title_stripped:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={"requests": [{"updateSheetProperties": {
                    "properties": {"sheetId": props["sheetId"], "title": title_stripped},
                    "fields": "title",
                }}]},
            ).execute()
            print(f"  → Renommé en : '{title_stripped}' (espace supprimé)")


FOLDER_CONNECTIONS = "1X_IDqTFPg-Hh-jkRnyTBnDjVmaXtgF_1"
FOLDER_MESSAGES    = "1Qd9yDA2N4kHSovlGA8aZavlAbQ3yeI2b"
FOLDER_LISTE_BRUTE = "1JCQvWRjGHH01wzgQDhVK9ho57xszIlI4"
FOLDER_ARCHIVES    = "1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh"
SHEET_TAB          = "ListeContacts_Lin_Out"
TEST_EMAIL         = "test.miner.diagnostic@example.com"


# ── TEST 1 : Google Sheets — écriture + lecture + nettoyage ──────────────────

def test_google_sheets() -> bool:
    print(f"\n{SEP}")
    print("TEST 1 : Google Sheets — écriture / lecture / nettoyage")
    print(SEP)

    from tools.google_sheets_tools import (
        _ecrire_contacts_sans_doublons,
        _get_sheets_service,
        SHEET_ID,
        COLONNES_SHEET,
    )

    contact_test = [{
        "Email":       TEST_EMAIL,
        "Prenom":      "Test",
        "Nom":         "DIAGNOSTIC",
        "Source":      "Test",
        "A_verifier":  "",
        "Domaine":     "example.com",
        "Statut":      "",
        "Extension":   ".com",
    }]

    print("→ Écriture du contact de test…")
    try:
        result = _ecrire_contacts_sans_doublons(SHEET_TAB, json.dumps(contact_test))
        print(f"  Résultat : {result}")
    except Exception as e:
        print(f"  ✗ Exception lors de l'écriture : {e}")
        return False

    # Lecture pour vérification
    try:
        service = _get_sheets_service()
        data = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=SHEET_TAB
        ).execute()
        rows = data.get("values", [])
        found = any(
            row and row[0] == TEST_EMAIL
            for row in rows[1:]
        )
        print(f"  Contact présent dans le Sheet : {'✓ OUI' if found else '✗ NON (bug !)'}")
    except Exception as e:
        print(f"  ✗ Exception lors de la lecture : {e}")
        return False

    # Nettoyage — supprimer la ligne de test
    try:
        lignes_propres = [r for r in rows if not (r and r[0] == TEST_EMAIL)]
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_TAB}!A1",
            valueInputOption="RAW",
            body={"values": lignes_propres},
        ).execute()
        print("  Contact de test supprimé (nettoyage OK).")
    except Exception as e:
        print(f"  ✗ Exception lors du nettoyage : {e}")

    return found


# ── TEST 2 : Google Drive — listage des dossiers clés ────────────────────────

def test_drive_listing():
    print(f"\n{SEP}")
    print("TEST 2 : Google Drive — contenu des dossiers")
    print(SEP)

    from tools.google_drive_tools import _get_drive_service
    service = _get_drive_service()

    dossiers = {
        "Connections (LinkedIn)": FOLDER_CONNECTIONS,
        "Messages   (LinkedIn)": FOLDER_MESSAGES,
        "Liste Brute (Nettoyeur)": FOLDER_LISTE_BRUTE,
        "Archives": FOLDER_ARCHIVES,
    }

    for nom, folder_id in dossiers.items():
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, size)",
            ).execute()
            files = results.get("files", [])
            if files:
                for f in files:
                    size_kb = int(f.get("size", 0)) // 1024
                    print(f"  [{nom}] {f['name']}  ({size_kb} ko)")
            else:
                print(f"  [{nom}] (vide)")
        except Exception as e:
            print(f"  [{nom}] ✗ Erreur : {e}")


# ── TEST 3 : Outlook — lecture sans filtre de date ───────────────────────────

def test_outlook_read():
    print(f"\n{SEP}")
    print("TEST 3 : Outlook — lecture des 50 derniers emails (sans filtre date)")
    print(SEP)

    os.environ.pop("OUTLOOK_SINCE_DT", None)

    from tools.outlook_tools import _lire_emails_outlook
    try:
        result = _lire_emails_outlook(top_par_dossier=50)
    except Exception as e:
        print(f"  ✗ Exception : {e}")
        return

    try:
        contacts = json.loads(result)
    except Exception as e:
        print(f"  ✗ JSON invalide : {e}\n  Brut : {result[:300]}")
        return

    if isinstance(contacts, dict) and "erreur" in contacts:
        print(f"  ✗ Erreur API : {contacts['erreur']}")
        return

    print(f"  Contacts valides extraits : {len(contacts)}")
    for c in contacts[:10]:
        print(f"    - {c.get('Email'):<40}  {c.get('Prenom')} {c.get('Nom')}")
    if len(contacts) > 10:
        print(f"    … et {len(contacts) - 10} autre(s)")


# ── TEST 4 : connections.csv — extraction ────────────────────────────────────

def test_connections_extraction():
    print(f"\n{SEP}")
    print("TEST 4 : connections.csv — extraction des contacts")
    print(SEP)

    from tools.google_drive_tools import _extraire_contacts_connections
    try:
        result = _extraire_contacts_connections(FOLDER_CONNECTIONS)
    except Exception as e:
        print(f"  ✗ Exception : {e}")
        return

    try:
        data = json.loads(result)
    except Exception as e:
        print(f"  ✗ JSON invalide : {e}\n  Brut : {result[:300]}")
        return

    if isinstance(data, dict) and "erreur" in data:
        print(f"  ✗ Erreur : {data['erreur']}")
        return

    print(f"  Contacts avec email trouvés : {len(data)}")
    for c in data[:5]:
        print(f"    - {c.get('Email')}")


# ── TEST 5 : messages.csv — extraction ───────────────────────────────────────

def test_messages_extraction():
    print(f"\n{SEP}")
    print("TEST 5 : messages.csv — extraction des contacts")
    print(SEP)

    from tools.google_drive_tools import _extraire_contacts_messages
    try:
        result = _extraire_contacts_messages(FOLDER_MESSAGES)
    except Exception as e:
        print(f"  ✗ Exception : {e}")
        return

    try:
        data = json.loads(result)
    except Exception as e:
        print(f"  ✗ JSON invalide : {e}\n  Brut : {result[:300]}")
        return

    if isinstance(data, dict) and "erreur" in data:
        print(f"  ✗ Erreur : {data['erreur']}")
        return

    print(f"  Contacts avec email trouvés : {len(data)}")
    for c in data[:5]:
        print(f"    - {c.get('Email')}")


# ── PIPELINE OUTLOOK BOUT EN BOUT (lecture + écriture réelle) ────────────────

def test_pipeline_outlook_complet():
    print(f"\n{SEP}")
    print("TEST 6 : Pipeline Outlook complet — fonctions Python directes (sans LLM)")
    print(SEP)

    os.environ.pop("OUTLOOK_SINCE_DT", None)  # sans filtre date = historique complet

    from tools.outlook_tools import _lire_emails_outlook
    from tools.google_sheets_tools import _ecrire_contacts_sans_doublons

    print("→ Lecture Outlook (50 derniers emails)…")
    try:
        contacts_json = _lire_emails_outlook(top_par_dossier=50)
        contacts = json.loads(contacts_json)
        if isinstance(contacts, dict) and "erreur" in contacts:
            print(f"  ✗ Erreur Outlook : {contacts['erreur']}")
            return
        print(f"  {len(contacts)} contact(s) extraits.")
    except Exception as e:
        print(f"  ✗ Exception lecture Outlook : {e}")
        return

    print("→ Écriture dans le Sheet…")
    try:
        result = _ecrire_contacts_sans_doublons(SHEET_TAB, contacts_json)
        print(f"  Résultat : {result}")
    except Exception as e:
        print(f"  ✗ Exception écriture Sheet : {e}")


# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("DIAGNOSTIC PIPELINE MINER")
    print("=" * 60)

    test_sheet_tabs()
    sheets_ok = test_google_sheets()
    test_drive_listing()
    test_outlook_read()
    test_connections_extraction()
    test_messages_extraction()
    test_pipeline_outlook_complet()

    print(f"\n{'=' * 60}")
    print(f"Sheets write/read : {'✓ OK' if sheets_ok else '✗ KO — bug critique'}")
    print("=" * 60)
