from crewai import Crew, Process
from llm import get_llm
from agents import (
    create_agent_extracteur_linkedin_connections,
    create_agent_extracteur_linkedin_messages,
    create_agent_extracteur_outlook,
    create_agent_nettoyeur,
)
from tasks import (
    create_task_extraction_connections,
    create_task_extraction_messages,
    create_task_extraction_outlook,
    create_task_nettoyage,
)


def build_crew() -> Crew:
    # LLM local partagé par tous les agents (deepseek-r1:8b via Ollama)
    llm = get_llm()

    # Agents
    ag_conn    = create_agent_extracteur_linkedin_connections(llm)
    ag_msg     = create_agent_extracteur_linkedin_messages(llm)
    ag_outlook = create_agent_extracteur_outlook(llm)
    ag_clean   = create_agent_nettoyeur(llm)

    # Tâches séquentielles : 1 → 2 → 3 → 4 (nettoyage)
    task_conn    = create_task_extraction_connections(ag_conn)
    task_msg     = create_task_extraction_messages(ag_msg)
    task_outlook = create_task_extraction_outlook(ag_outlook)
    task_clean   = create_task_nettoyage(ag_clean, context=[task_conn, task_msg, task_outlook])

    return Crew(
        agents=[ag_conn, ag_msg, ag_outlook, ag_clean],
        tasks=[task_conn, task_msg, task_outlook, task_clean],
        process=Process.sequential,
        verbose=False,
    )
