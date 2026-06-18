from crewai import Agent
from langchain_ollama import ChatOllama
from tools.google_drive_tools import extraire_contacts_messages, archiver_fichier_drive
from tools.google_sheets_tools import ecrire_contacts_sans_doublons


def create_agent_extracteur_linkedin_messages(llm: ChatOllama) -> Agent:
    """
    Agent 2 — Extracteur_Linkedin_messages
    Déclenché par la présence du fichier messages.csv dans le dossier Drive
    'Linkedin_messages_file'. Extrait les contacts depuis les colonnes FROM/TO,
    cherche les emails dans le contenu des messages, et écrit dans le Google Sheet
    avec les colonnes exactes : Email, Prenom, Nom, Source, Domaine, Extension.
    Les colonnes 'A vérifier' et 'Statut' sont laissées vides.
    """
    return Agent(
        role="Extracteur des messages LinkedIn",
        goal=(
            "Lire le fichier messages.csv depuis Google Drive et écrire chaque contact "
            "tiers identifié dans le Google Sheet avec les colonnes suivantes :\n"
            "- Email : adresse email en minuscules (extraite du contenu du message si présente)\n"
            "- Prenom : première lettre en majuscule\n"
            "- Nom : entièrement en MAJUSCULES\n"
            "- Source : toujours 'Linkedin'\n"
            "- A vérifier : laisser VIDE (ne pas remplir)\n"
            "- Domaine : domaine de l'email (ex. gmail.com) — vide si pas d'email\n"
            "- Statut : laisser VIDE (ne pas remplir)\n"
            "- Extension : extension du domaine (ex. .com) — vide si pas d'email\n"
            "Exclure le propriétaire du compte et les contacts 'LinkedIn Member'.\n"
            "Avant d'écrire, vérifier les doublons : conserver la version déjà présente."
        ),
        backstory=(
            "Agent spécialisé dans l'extraction de contacts depuis les échanges LinkedIn. "
            "Tu sais identifier les interlocuteurs réels dans un fil de messages, "
            "extraire les emails mentionnés dans les contenus, et formater chaque contact "
            "selon les règles exactes du Google Sheet de contacts. "
            "RÈGLE ABSOLUE : tu es un robot d'exécution, pas un narrateur. "
            "Tu ne décris JAMAIS ce que tu vas faire et ne simules JAMAIS un appel d'outil "
            "dans ta réponse textuelle. Chaque étape doit être accomplie en appelant "
            "RÉELLEMENT l'outil Python correspondant via l'interface d'appel d'outil. "
            "Si l'outil n'a pas été exécuté techniquement, la tâche n'est pas faite."
        ),
        tools=[extraire_contacts_messages, ecrire_contacts_sans_doublons, archiver_fichier_drive],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
