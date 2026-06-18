"""Crew dédié à l'agent 3 — Extracteur Outlook."""
from crewai import Crew, Process
from dotenv import load_dotenv
from llm import get_llm
from agents.agent_extracteur_outlook import create_agent_extracteur_outlook
from tasks.tasks import create_task_extraction_outlook

load_dotenv()


def run_outlook() -> str:
    llm   = get_llm()
    agent = create_agent_extracteur_outlook(llm)
    task  = create_task_extraction_outlook(agent)
    crew  = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    return str(crew.kickoff())


if __name__ == "__main__":
    print(run_outlook())
