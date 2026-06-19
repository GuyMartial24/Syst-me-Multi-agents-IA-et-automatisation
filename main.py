from dotenv import load_dotenv
from crews.crew import build_crew

load_dotenv()


def main():
    print("=== MINER — Construction automatique de la liste de contacts ===\n")
    print("Sources : LinkedIn connections | LinkedIn messages | Outlook Pierre Bono")
    print("Destination : Google Sheet ListeContacts_Lin_Out_FINAL\n")

    crew = build_crew()
    result = crew.kickoff()

    print("\n=== Résultat final ===")
    print(result)


if __name__ == "__main__":
    main()
