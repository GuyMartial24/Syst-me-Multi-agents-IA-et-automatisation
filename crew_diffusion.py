"""
Crew dédié à la diffusion email.
Lancé automatiquement par monitor_diffusion.py quand un nouveau fichier
ListeContacts_Lin_Out_FINAL est détecté dans le dossier Drive Diffusion_et_Communication.
"""
from crewai import Crew, Process
from dotenv import load_dotenv

from llm import get_llm
from agents.agent_diffusion_et_com import create_agent_diffusion_et_com
from tasks.task_diffusion import create_task_diffusion

load_dotenv()


def run_diffusion() -> str:
    llm = get_llm()
    agent = create_agent_diffusion_et_com(llm)
    task  = create_task_diffusion(agent)

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    print(run_diffusion())
