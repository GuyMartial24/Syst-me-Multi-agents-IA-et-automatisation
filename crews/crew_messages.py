"""Crew dédié à l'agent 2 — Extracteur LinkedIn Messages."""
from crewai import Crew, Process
from dotenv import load_dotenv
from llm import get_llm
from agents.agent_extracteur_linkedin_messages import create_agent_extracteur_linkedin_messages
from tasks.tasks import create_task_extraction_messages

load_dotenv()


def run_messages() -> str:
    llm = get_llm()
    agent = create_agent_extracteur_linkedin_messages(llm)
    task = create_task_extraction_messages(agent)
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
        use_native_tools=True,
    )
    return str(crew.kickoff())


if __name__ == "__main__":
    print(run_messages())
