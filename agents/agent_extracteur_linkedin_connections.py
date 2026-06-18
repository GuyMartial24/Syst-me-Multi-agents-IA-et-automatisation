from crewai import Agent
from langchain_ollama import ChatOllama
from tools.google_drive_tools import extraire_contacts_connections, archiver_fichier_drive
from tools.google_sheets_tools import ecrire_contacts_sans_doublons


def create_agent_extracteur_linkedin_connections(llm: ChatOllama) -> Agent:
    """
    Agent 1 — Extracteur_Linkedin_connections
    Déclenché par la présence du fichier connections.csv dans le dossier Drive
    'Linkedin_connections_file'. Formate et écrit les contacts dans le Google Sheet
    avec les colonnes exactes : Email, Prenom, Nom, Source, Domaine, Extension.
    Les colonnes 'A vérifier' et 'Statut' sont laissées vides.
    """
    return Agent(
        role="Extracteur des connexions LinkedIn",
        goal=(
            "Lire le fichier connections.csv depuis Google Drive et écrire chaque contact "
            "dans le Google Sheet avec les colonnes suivantes :\n"
            "- Email : adresse email en minuscules\n"
            "- Prenom : première lettre en majuscule\n"
            "- Nom : entièrement en MAJUSCULES\n"
            "- Source : toujours 'Linkedin'\n"
            "- A vérifier : laisser VIDE (ne pas remplir)\n"
            "- Domaine : domaine de l'email (ex. gmail.com)\n"
            "- Statut : laisser VIDE (ne pas remplir)\n"
            "- Extension : extension du domaine (ex. .com)\n"
            "Seuls les contacts ayant une adresse email valide sont inclus."
        ),
        backstory=(
            "Agent spécialisé dans l'extraction et le formatage des données LinkedIn. "
            "Tu sais précisément comment transformer les données brutes du fichier "
            "connections.csv en entrées propres dans le Google Sheet de contacts, "
            "en respectant scrupuleusement les règles de formatage de chaque colonne."
        ),
        tools=[extraire_contacts_connections, ecrire_contacts_sans_doublons, archiver_fichier_drive],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
