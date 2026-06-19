from crewai import Task, Agent

# IDs des dossiers Google Drive
FOLDER_LINKEDIN_CONNECTIONS = "1X_IDqTFPg-Hh-jkRnyTBnDjVmaXtgF_1"
FOLDER_LINKEDIN_MESSAGES = "1Qd9yDA2N4kHSovlGA8aZavlAbQ3yeI2b"
FOLDER_LISTE_BRUTE = "1JCQvWRjGHH01wzgQDhVK9ho57xszIlI4"
FOLDER_LISTE_FINALE = "1JjFDdTs2yt-fp2j795i2TUxI9fuKkGUG"
FOLDER_ARCHIVES = "1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh"

# Onglet unique du Google Sheet principal (convention : nom fichier = nom onglet)
ONGLET_CONTACTS = "ListeContacts_Lin_Out"


def create_task_extraction_connections(agent: Agent) -> Task:
    return Task(
        description=(
            f"Appelle l'outil 'traiter_fichier_connections' avec "
            f"folder_id='{FOLDER_LINKEDIN_CONNECTIONS}'. "
            "L'outil extrait les contacts de connections.csv, les écrit dans "
            f"l'onglet '{ONGLET_CONTACTS}' du Google Sheet, et archive le fichier. "
            "Restitue sa sortie brute sans aucun ajout de texte."
        ),
        expected_output=(
            "Sortie brute de l'outil, par exemple :\n"
            "Traitement terminé.\n"
            f"Écriture  : X contact(s) ajouté(s) dans '{ONGLET_CONTACTS}'. ...\n"
            "Archivage : connections.csv → connections_JJMMAAAA.csv."
        ),
        agent=agent,
    )


def create_task_extraction_messages(agent: Agent) -> Task:
    return Task(
        description=(
            f"Appelle l'outil 'traiter_fichier_messages' avec "
            f"folder_id='{FOLDER_LINKEDIN_MESSAGES}'. "
            "L'outil extrait les contacts de messages.csv, les écrit dans "
            f"l'onglet '{ONGLET_CONTACTS}' du Google Sheet, et archive le fichier. "
            "Restitue sa sortie brute sans aucun ajout de texte."
        ),
        expected_output=(
            "Sortie brute de l'outil, par exemple :\n"
            "Traitement terminé.\n"
            f"Écriture  : X contact(s) ajouté(s) dans '{ONGLET_CONTACTS}'. ...\n"
            "Archivage : messages.csv → messages_JJMMAAAA.csv."
        ),
        agent=agent,
    )


def create_task_extraction_outlook(agent: Agent) -> Task:
    return Task(
        description=(
            "Appelle l'outil 'traiter_emails_outlook' sans paramètre. "
            "L'outil lit les emails Outlook (Inbox + SentItems), extrait les contacts réels "
            f"et les écrit dans l'onglet '{ONGLET_CONTACTS}' du Google Sheet. "
            "Restitue sa sortie brute sans aucun ajout de texte."
        ),
        expected_output=(
            "Sortie brute de l'outil, par exemple :\n"
            "Traitement terminé.\n"
            f"Écriture : X contact(s) ajouté(s) dans '{ONGLET_CONTACTS}'. ..."
        ),
        agent=agent,
    )


def create_task_nettoyage(agent: Agent, context: list) -> Task:
    return Task(
        description=(
            f"Appelle l'outil 'traiter_liste_contacts' avec "
            f"folder_id='{FOLDER_LISTE_BRUTE}' et filename='ListeContacts_Lin_Out'. "
            "L'outil lit le fichier Excel, nettoie les contacts en mémoire "
            "(A verifier=1, exclusions, doublons), crée le fichier FINAL dans ListeFinale "
            "et archive le fichier source. "
            "Restitue sa sortie brute sans aucun ajout de texte."
        ),
        expected_output=(
            "Sortie brute de l'outil, par exemple :\n"
            "Nettoyage terminé.\n"
            "  Contacts bruts lus        : N\n"
            "  Fichier créé              : ListeContacts_Lin_Out_FINAL_JJMMAAAA.xlsx\n"
            "Archivage : ListeContacts_Lin_Out → ListeContacts_Lin_Out_JJMMAAAA."
        ),
        agent=agent,
        context=context,
    )
