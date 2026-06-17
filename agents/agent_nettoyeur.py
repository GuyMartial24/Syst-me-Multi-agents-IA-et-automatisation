from crewai import Agent
from langchain_ollama import ChatOllama
from tools.google_sheets_tools import (
    lire_google_sheet,
    supprimer_lignes_a_verifier,
    supprimer_emails_exclus,
    dedoublonner_google_sheet,
    ecrire_dans_google_sheet,
)
from tools.google_drive_tools import archiver_fichier_drive


def create_agent_nettoyeur(llm: ChatOllama) -> Agent:
    """
    Agent 4 — Nettoyeur
    Déclenché par la présence d'un fichier dans le dossier Drive 'ListeContacts_Lin_Out_brute'.
    Supprime les lignes où 'A vérifier' = 1, dédoublonne, écrit le résultat final dans
    le Google Sheet 'ListeFinale', puis archive le fichier déclencheur avec la date dans
    le nom et vide le dossier ListeContacts_Lin_Out_brute.
    """
    return Agent(
        role="Nettoyeur et dédoublonneur de la liste de contacts",
        goal=(
            "Nettoyer le Google Sheet principal en trois passes successives sur "
            "l'onglet 'ListeContacts_Lin_Out_FINAL' :\n"
            "1. Supprimer toutes les lignes dont la colonne 'A vérifier' = 1.\n"
            "2. Supprimer toutes les lignes dont l'email figure dans ListeExclusion "
            "(colonne 'Emails exclus', ID : 1sz7xUM05y6xI-bj1Wz8jvmOzuIH7ZzCoEyECgqkZ9xc).\n"
            "3. Supprimer les doublons sur la colonne 'Email'.\n"
            "Enfin, archiver les fichiers du dossier 'ListeContacts_Lin_Out_brute' "
            "vers le dossier 'Archives' en ajoutant la date du jour dans leur nom "
            "(format : nom_jjmmaaaa.ext), afin de vider le dossier source."
        ),
        backstory=(
            "Agent chargé de la qualité finale de la liste de contacts. "
            "Tu supprimes les entrées à problèmes, les adresses indésirables issues "
            "de la liste d'exclusion, élimines les doublons, "
            "et t'assures que chaque dossier source est vidé après traitement "
            "en archivant les fichiers avec un horodatage clair."
        ),
        tools=[
            lire_google_sheet,
            supprimer_lignes_a_verifier,
            supprimer_emails_exclus,
            dedoublonner_google_sheet,
            ecrire_dans_google_sheet,
            archiver_fichier_drive,
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
