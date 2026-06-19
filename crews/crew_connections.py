"""Crew dédié à l'agent 1 — Extracteur LinkedIn Connections."""
from crewai import Crew, Process
from dotenv import load_dotenv
from llm import get_llm
from agents.agent_extracteur_linkedin_connections import (
    create_agent_extracteur_linkedin_connections,
)
from tasks.tasks import create_task_extraction_connections

load_dotenv()


def run_connections() -> str:
    llm = get_llm()
    agent = create_agent_extracteur_linkedin_connections(llm)
    task = create_task_extraction_connections(agent)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
        use_native_tools=True,
    )
    return str(crew.kickoff())


if __name__ == "__main__":
    print(run_connections())
