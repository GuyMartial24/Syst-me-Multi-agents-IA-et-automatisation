from crewai import Agent, LLM
from tools.pipeline_tools import traiter_fichier_messages


def create_agent_extracteur_linkedin_messages(llm: LLM) -> Agent:
    """
    Agent 2 — Extracteur_Linkedin_messages
    Déclenché par la présence de messages.csv dans le dossier Drive
    'Linkedin_messages_file'. Dispose d'un seul outil qui gère en une passe
    l'extraction, l'écriture dans le Google Sheet et l'archivage du fichier.
    """
    return Agent(
        role="Extracteur des messages LinkedIn",
        goal=(
            "Appeler l'outil 'traiter_fichier_messages' avec le folder_id fourni. "
            "L'outil extrait les contacts de messages.csv, les écrit dans le "
            "Google Sheet et archive le fichier en une seule opération atomique. "
            "Restituer sa sortie brute sans aucun ajout de texte."
        ),
        backstory=(
            "Agent spécialisé dans le traitement du fichier messages.csv LinkedIn. "
            "Tu disposes d'un seul outil qui gère les trois étapes en une opération. "
            "RÈGLE ABSOLUE : appelle l'outil immédiatement sans narration préalable. "
            "Ne décris jamais ce que tu vas faire — déclenche l'outil directement."
        ),
        tools=[traiter_fichier_messages],
        llm=llm,
        verbose=True,  # Activé pour tracer le raisonnement de l'agent pas à pas
        allow_delegation=False,
    )
