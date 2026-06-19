"""
Outils pipeline : toutes les étapes d'un agent en une seule opération atomique.
Conçus pour llama3.1 qui ne chaîne pas fiablement plusieurs appels d'outils.
Le LLM n'a qu'un seul outil à appeler ; la séquence est garantie côté Python.
"""
import json
from crewai.tools import tool
from tools.google_drive_tools import (
    _extraire_contacts_connections,
    _extraire_contacts_messages,
    _archiver_fichier,
)
from tools.google_sheets_tools import _ecrire_contacts_sans_doublons
from tools.outlook_tools import _lire_emails_outlook
from tools.nettoyeur_tools import (
    _lire_contacts_depuis_excel_drive,
    _lire_liste_exclusion,
    _creer_excel_nettoye_dans_drive,
)

ONGLET_CONTACTS = "ListeContacts_Lin_Out"
FOLDER_ARCHIVES = "1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh"
FOLDER_LISTE_FINALE = "1JjFDdTs2yt-fp2j795i2TUxI9fuKkGUG"


@tool("Traiter le fichier connections.csv LinkedIn de bout en bout")
def traiter_fichier_connections(folder_id: str) -> str:
    """
    Traite connections.csv depuis un dossier Google Drive en trois étapes atomiques :
    1. Extrait et formate les contacts (Email, Prenom, Nom, Source, Domaine, Extension).
    2. Écrit les nouveaux contacts dans le Google Sheet ListeContacts_Lin_Out (sans doublons).
    3. Archive connections.csv avec la date dans le nom dans le dossier Archives.
    Paramètre : folder_id = ID du dossier Google Drive contenant connections.csv.
    """
    # Étape 1 : extraction
    contacts_json = _extraire_contacts_connections(folder_id)
    try:
        parsed = json.loads(contacts_json)
    except json.JSONDecodeError:
        return f"Erreur JSON lors de l'extraction : {contacts_json[:300]}"

    if isinstance(parsed, dict) and "erreur" in parsed:
        return f"Extraction impossible : {parsed['erreur']}"

    # Étape 2 : écriture dans le Sheet (même si liste vide, on le signale)
    resultat_ecriture = _ecrire_contacts_sans_doublons(ONGLET_CONTACTS, contacts_json)

    # Étape 3 : archivage (le fichier source est traité, on le retire du dossier)
    resultat_archive = _archiver_fichier(folder_id, FOLDER_ARCHIVES, "connections.csv")

    return (
        "Traitement terminé.\n"
        f"Écriture  : {resultat_ecriture}\n"
        f"Archivage : {resultat_archive}"
    )


@tool("Traiter le fichier messages.csv LinkedIn de bout en bout")
def traiter_fichier_messages(folder_id: str) -> str:
    """
    Traite messages.csv depuis un dossier Google Drive en trois étapes atomiques :
    1. Extrait et formate les contacts identifiés dans les colonnes FROM/TO.
    2. Écrit les nouveaux contacts dans le Google Sheet ListeContacts_Lin_Out (sans doublons).
    3. Archive messages.csv avec la date dans le nom dans le dossier Archives.
    Paramètre : folder_id = ID du dossier Google Drive contenant messages.csv.
    """
    # Étape 1 : extraction
    contacts_json = _extraire_contacts_messages(folder_id)
    try:
        parsed = json.loads(contacts_json)
    except json.JSONDecodeError:
        return f"Erreur JSON lors de l'extraction : {contacts_json[:300]}"

    if isinstance(parsed, dict) and "erreur" in parsed:
        return f"Extraction impossible : {parsed['erreur']}"

    # Étape 2 : écriture dans le Sheet (même si liste vide, on le signale)
    resultat_ecriture = _ecrire_contacts_sans_doublons(ONGLET_CONTACTS, contacts_json)

    # Étape 3 : archivage (le fichier source est traité, on le retire du dossier)
    resultat_archive = _archiver_fichier(folder_id, FOLDER_ARCHIVES, "messages.csv")

    return (
        "Traitement terminé.\n"
        f"Écriture  : {resultat_ecriture}\n"
        f"Archivage : {resultat_archive}"
    )


@tool("Traiter les emails Outlook de Pierre Bono de bout en bout")
def traiter_emails_outlook(top_par_dossier: int = 100) -> str:
    """
    Traite la boîte Outlook de Pierre Bono en deux étapes atomiques :
    1. Lit les emails entrants (Inbox) et sortants (SentItems) via Microsoft Graph API
       et extrait les contacts réels (From, To, Cc) en excluant Pierre Bono
       et les adresses automatiques (no-reply, newsletters, notifications).
    2. Écrit les nouveaux contacts dans le Google Sheet ListeContacts_Lin_Out (sans doublons).
    Paramètre optionnel : top_par_dossier = nombre max de messages par dossier (défaut 100).
    """
    # Étape 1 : lecture Outlook
    contacts_json = _lire_emails_outlook(top_par_dossier)
    try:
        parsed = json.loads(contacts_json)
    except json.JSONDecodeError:
        return f"Erreur JSON lors de la lecture Outlook : {contacts_json[:300]}"

    if isinstance(parsed, dict) and "erreur" in parsed:
        return f"Lecture Outlook impossible : {parsed['erreur']}"

    # Étape 2 : écriture dans le Sheet
    resultat_ecriture = _ecrire_contacts_sans_doublons(ONGLET_CONTACTS, contacts_json)

    return (
        "Traitement terminé.\n"
        f"Écriture : {resultat_ecriture}"
    )


@tool("Traiter la liste de contacts brute : nettoyage et création du fichier FINAL")
def traiter_liste_contacts(folder_id: str, filename: str) -> str:
    """
    Traite le fichier Excel ListeContacts_Lin_Out en quatre étapes atomiques :
    1. Lit les contacts depuis le fichier Excel dans le dossier Drive folder_id.
    2. Lit la liste d'exclusion depuis le Google Sheet ListeExclusion.
    3. Nettoie en mémoire (A verifier=1, exclusions, doublons) et crée
       ListeContacts_Lin_Out_FINAL_jjmmaaaa.xlsx dans le dossier ListeFinale.
    4. Archive le fichier source avec la date dans le nom dans le dossier Archives.
    Paramètres : folder_id = dossier source, filename = nom du fichier Excel.
    """
    # Étape 1 : lire les contacts depuis le fichier Excel Drive
    contacts_json = _lire_contacts_depuis_excel_drive(folder_id, filename)
    try:
        parsed = json.loads(contacts_json)
    except json.JSONDecodeError:
        return f"Erreur JSON lors de la lecture Excel : {contacts_json[:300]}"

    if isinstance(parsed, dict) and "erreur" in parsed:
        return f"Lecture Excel impossible : {parsed['erreur']}"

    # Étape 2 : lire la liste d'exclusion
    exclusions_json = _lire_liste_exclusion()

    # Étape 3 : nettoyer et créer le fichier FINAL dans ListeFinale
    rapport_nettoyage = _creer_excel_nettoye_dans_drive(
        contacts_json, exclusions_json, FOLDER_LISTE_FINALE
    )

    # Étape 4 : archiver tous les fichiers du dossier source
    # (pas de filtre par nom : le fichier peut s'appeler avec ou sans .xlsx)
    resultat_archive = _archiver_fichier(folder_id, FOLDER_ARCHIVES)

    return (
        f"{rapport_nettoyage}\n"
        f"Archivage : {resultat_archive}"
    )
