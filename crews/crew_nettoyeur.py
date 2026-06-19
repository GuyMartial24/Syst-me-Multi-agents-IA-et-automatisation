"""Crew dédié à l'agent 4 — Nettoyeur."""
from crewai import Crew, Process
from dotenv import load_dotenv
from llm import get_llm
from agents.agent_nettoyeur import create_agent_nettoyeur
from tasks.tasks import create_task_nettoyage

load_dotenv()


def run_nettoyeur() -> str:
    llm = get_llm()
    agent = create_agent_nettoyeur(llm)
    # context=[] : déclenché seul par le monitor, sans attendre d'autres tâches
    task = create_task_nettoyage(agent, context=[])
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
        use_native_tools=True,
    )
    return str(crew.kickoff())


if __name__ == "__main__":
    print(run_nettoyeur())
