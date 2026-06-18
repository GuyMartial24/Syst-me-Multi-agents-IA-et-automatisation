from crewai import Agent
from langchain_ollama import ChatOllama
from tools.outlook_tools import lire_emails_outlook
from tools.google_sheets_tools import ecrire_contacts_sans_doublons


def create_agent_extracteur_outlook(llm: ChatOllama) -> Agent:
    """
    Agent 3 — Extracteur_Outlook
    Déclenché par l'arrivée ou le départ d'un email dans la boîte de Pierre Bono.
    Lit les dossiers Inbox et SentItems via Microsoft Graph API.
    Extrait tous les contacts réels (From, To, Cc), en excluant Pierre Bono,
    les adresses no-reply, newsletters et notifications automatiques.
    Écrit dans le Google Sheet avec les colonnes exactes.
    """
    return Agent(
        role="Extracteur de la boîte Outlook de Pierre Bono",
        goal=(
            "Lire les emails entrants (Inbox) et sortants (SentItems) de la boîte "
            "Outlook de Pierre Bono via l'API Microsoft Graph, et écrire chaque "
            "contact réel identifié dans le Google Sheet avec les colonnes suivantes :\n"
            "- Email : adresse email en minuscules\n"
            "- Prenom : première lettre en majuscule\n"
            "- Nom : entièrement en MAJUSCULES\n"
            "- Source : toujours 'Outlook'\n"
            "- A vérifier : laisser VIDE (ne pas remplir)\n"
            "- Domaine : domaine de l'email (ex. f-r-d.fr)\n"
            "- Statut : laisser VIDE (ne pas remplir)\n"
            "- Extension : extension du domaine (ex. .fr)\n"
            "Règles d'exclusion appliquées automatiquement par le tool :\n"
            "- Pierre Bono (pierre.bono@f-r-d.fr) — propriétaire de la boîte\n"
            "- Adresses no-reply / do-not-reply / nepasrepondre\n"
            "- Adresses de newsletters et mailings automatiques\n"
            "- Adresses de notifications système (notification, alert, update, etc.)\n"
            "- Adresses génériques : noreply, admin, support, contact, marketing, "
            "robot, postmaster, mailer-daemon, bounce\n"
            "Seuls les contacts humains réels sont conservés.\n"
            "Avant d'écrire, vérifier les doublons : conserver la version déjà présente."
        ),
        backstory=(
            "Agent spécialisé dans l'extraction de contacts humains depuis une boîte "
            "email professionnelle. Tu maîtrises l'API Microsoft Graph et sais naviguer "
            "dans les dossiers Inbox et SentItems pour identifier tous les vrais "
            "interlocuteurs de Pierre Bono. Tu filtres automatiquement les expéditeurs "
            "automatiques (no-reply, newsletters, notifications, systèmes) pour ne "
            "conserver que les contacts humains, en respectant scrupuleusement "
            "le format du Google Sheet."
        ),
        tools=[lire_emails_outlook, ecrire_contacts_sans_doublons],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
