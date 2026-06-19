from crewai import Task, Agent

FOLDER_DIFFUSION = "1peQ9728pAY2h2j60i-Wns4-bXyjZzVzl"
FOLDER_ARCHIVES = "1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh"


def create_task_diffusion(agent: Agent) -> Task:
    return Task(
        description=(
            "Étape 1 — Lecture des destinataires :\n"
            f"Utilise l'outil 'lire_emails_depuis_excel_drive' avec "
            f"folder_id='{FOLDER_DIFFUSION}' pour lire la liste des adresses email "
            "depuis le fichier Excel daté 'ListeContacts_Lin_Out_FINAL_jjmmaaaa.xlsx'. "
            "L'outil recherche automatiquement par préfixe et retourne un JSON :\n"
            "  {\"fichier\": \"ListeContacts_Lin_Out_FINAL_jjmmaaaa.xlsx\", \"emails\": [...]}\n"
            "Note : retiens la valeur du champ 'fichier' — elle sera utilisée à l'étape 4.\n\n"
            "Étape 2 — Lecture du message :\n"
            "Utilise l'outil 'lire_contenu_message_depuis_drive' (sans paramètre) "
            "pour lire le fichier 'ContenuMessage.docx' (format .docx, ID fixe dans Google Drive). "
            "Ce fichier contient :\n"
            "  • Une ligne commençant par 'Objet :' (espace avant ':') "
            "→ c'est le sujet de l'email.\n"
            "  • Le reste du texte → c'est le corps du message.\n"
            "L'outil retourne un JSON {\"objet\": \"...\", \"corps\": \"...\"}.\n\n"
            "Étape 3 — Envoi des emails :\n"
            "Utilise l'outil 'envoyer_emails_via_sendinblue' avec :\n"
            "  • emails_json : le JSON array du champ 'emails' extrait à l'étape 1\n"
            "  • sujet       : le champ 'objet' extrait à l'étape 2\n"
            "  • contenu     : le champ 'corps' extrait à l'étape 2\n"
            "Le même message est envoyé à tous les destinataires sans personnalisation. "
            "L'expéditeur est défini dans les variables d'environnement "
            "(SENDINBLUE_SENDER_EMAIL, SENDINBLUE_SENDER_NAME).\n\n"
            "Étape 4 — Archivage :\n"
            f"Utilise l'outil 'archiver_fichier_drive' avec "
            f"source_folder_id='{FOLDER_DIFFUSION}', "
            f"archives_folder_id='{FOLDER_ARCHIVES}' et "
            "filename=<valeur du champ 'fichier' obtenue à l'étape 1> pour archiver "
            "le fichier Excel traité et éviter un double envoi. "
            "Le fichier 'ContenuMessage' reste dans le dossier (réutilisable).\n"
            "EXIGENCE CRITIQUE : chaque étape doit être réalisée en déclenchant RÉELLEMENT "
            "l'outil Python correspondant. Ne jamais décrire ou simuler un appel d'outil — "
            "déclencher l'outil directement et restituer sa sortie brute."
        ),
        expected_output=(
            "Sortie brute des 4 outils exécutés, sans prose ni commentaire :\n"
            "1. Résultat de lire_emails_depuis_excel_drive : JSON {fichier, emails}.\n"
            "2. Résultat de lire_contenu_message_depuis_drive : JSON {objet, corps}.\n"
            "3. Résultat de envoyer_emails_via_sendinblue : 'X email(s) envoyé(s), Y échec(s).'\n"
            "4. Résultat de archiver_fichier_drive : nom du fichier archivé avec horodatage."
        ),
        agent=agent,
    )
