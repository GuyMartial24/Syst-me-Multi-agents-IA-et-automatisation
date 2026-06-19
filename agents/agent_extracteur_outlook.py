from crewai import Agent, LLM
from tools.pipeline_tools import traiter_emails_outlook


def create_agent_extracteur_outlook(llm: LLM) -> Agent:
    """
    Agent 3 — Extracteur_Outlook
    Déclenché par l'arrivée ou le départ d'un email dans la boîte de Pierre Bono.
    Dispose d'un seul outil qui lit les emails Outlook et écrit les contacts
    dans le Google Sheet en une seule opération atomique.
    """
    return Agent(
        role="Extracteur de la boîte Outlook de Pierre Bono",
        goal=(
            "Appeler l'outil 'traiter_emails_outlook' sans paramètre. "
            "L'outil lit les emails Outlook (Inbox + SentItems), extrait les contacts "
            "réels et les écrit dans le Google Sheet en une seule opération. "
            "Restituer sa sortie brute sans aucun ajout de texte."
        ),
        backstory=(
            "Agent spécialisé dans l'extraction de contacts depuis la boîte Outlook. "
            "Tu disposes d'un seul outil qui gère les deux étapes en une opération. "
            "RÈGLE ABSOLUE : appelle l'outil immédiatement sans narration préalable. "
            "Ne décris jamais ce que tu vas faire — déclenche l'outil directement."
        ),
        tools=[traiter_emails_outlook],
        llm=llm,
        verbose=True,  # Activé pour tracer le raisonnement de l'agent pas à pas
        allow_delegation=False,
    )
