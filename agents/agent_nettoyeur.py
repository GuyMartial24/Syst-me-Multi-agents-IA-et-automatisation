from crewai import Agent, LLM
from tools.pipeline_tools import traiter_liste_contacts


def create_agent_nettoyeur(llm: LLM) -> Agent:
    """
    Agent 4 — Nettoyeur
    Déclenché par la présence du fichier ListeContacts_Lin_Out dans ListeContacts_Lin_Out_brute.
    Dispose d'un seul outil qui lit le fichier Excel, nettoie les contacts en mémoire
    (A verifier, exclusions, doublons), crée le fichier FINAL dans ListeFinale,
    puis archive le fichier source. Tout en une seule opération atomique.
    """
    return Agent(
        role="Nettoyeur et dédoublonneur de la liste de contacts",
        goal=(
            "Appeler l'outil 'traiter_liste_contacts' avec les paramètres folder_id et filename "
            "fournis dans la tâche. L'outil lit le fichier Excel, nettoie les contacts en mémoire, "
            "crée le fichier FINAL dans ListeFinale et archive le fichier source. "
            "Restituer sa sortie brute sans aucun ajout de texte."
        ),
        backstory=(
            "Agent chargé de la qualité finale de la liste de contacts. "
            "Tu disposes d'un seul outil qui gère les quatre étapes en une opération atomique : "
            "lecture Excel, lecture exclusions, nettoyage + création du fichier FINAL, archivage. "
            "RÈGLE ABSOLUE : appelle l'outil immédiatement sans narration préalable. "
            "Ne décris jamais ce que tu vas faire — déclenche l'outil directement."
        ),
        tools=[traiter_liste_contacts],
        llm=llm,
        verbose=True,  # Activé pour tracer le raisonnement de l'agent pas à pas
        allow_delegation=False,
    )
