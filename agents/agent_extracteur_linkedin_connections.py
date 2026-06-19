from crewai import Agent, LLM
from tools.pipeline_tools import traiter_fichier_connections


def create_agent_extracteur_linkedin_connections(llm: LLM) -> Agent:
    """
    Agent 1 — Extracteur_Linkedin_connections
    Déclenché par la présence de connections.csv dans le dossier Drive
    'Linkedin_connections_file'. Dispose d'un seul outil qui gère en une passe
    l'extraction, l'écriture dans le Google Sheet et l'archivage du fichier.
    """
    return Agent(
        role="Extracteur des connexions LinkedIn",
        goal=(
            "Appeler l'outil 'traiter_fichier_connections' avec le folder_id fourni. "
            "L'outil extrait les contacts de connections.csv, les écrit dans le "
            "Google Sheet et archive le fichier en une seule opération atomique. "
            "Restituer sa sortie brute sans aucun ajout de texte."
        ),
        backstory=(
            "Agent spécialisé dans le traitement du fichier connections.csv LinkedIn. "
            "Tu disposes d'un seul outil qui gère les trois étapes en une opération. "
            "RÈGLE ABSOLUE : appelle l'outil immédiatement sans narration préalable. "
            "Ne décris jamais ce que tu vas faire — déclenche l'outil directement."
        ),
        tools=[traiter_fichier_connections],
        llm=llm,
        verbose=True,  # Activé pour tracer le raisonnement de l'agent pas à pas
        allow_delegation=False,
    )
