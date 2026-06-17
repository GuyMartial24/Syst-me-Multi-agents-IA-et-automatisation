from crewai import Task, Agent

FOLDER_DIFFUSION = "1peQ9728pAY2h2j60i-Wns4-bXyjZzVzl"
FOLDER_ARCHIVES  = "1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh"


def create_task_diffusion(agent: Agent) -> Task:
    return Task(
        description=(
            "Étape 1 — Lecture des destinataires :\n"
            f"Utilise l'outil 'lire_emails_depuis_excel_drive' avec "
            f"folder_id='{FOLDER_DIFFUSION}' pour lire la liste des adresses email "
            "depuis le fichier Excel 'ListeContacts_Lin_Out_FINAL'. "
            "Seules les adresses valides (contenant '@') sont retenues.\n\n"
            "Étape 2 — Lecture du message :\n"
            "Utilise l'outil 'lire_contenu_message_depuis_drive' (sans paramètre) "
            "pour lire le fichier 'ContenuMessage.docx' (format .docx, ID fixe dans Google Drive). "
            "Ce fichier contient :\n"
            "  • Une ligne commençant par 'Objet:' → c'est le sujet de l'email.\n"
            "  • Le reste du texte → c'est le corps du message.\n"
            "L'outil retourne un JSON {\"objet\": \"...\", \"corps\": \"...\"}.\n\n"
            "Étape 3 — Envoi des emails :\n"
            "Utilise l'outil 'envoyer_emails_via_sendinblue' avec :\n"
            "  • emails_json : la liste JSON des emails de l'étape 1\n"
            "  • sujet       : le champ 'objet' extrait à l'étape 2\n"
            "  • contenu     : le champ 'corps' extrait à l'étape 2\n"
            "Le même message est envoyé à tous les destinataires sans personnalisation. "
            "L'expéditeur est défini dans les variables d'environnement "
            "(SENDINBLUE_SENDER_EMAIL, SENDINBLUE_SENDER_NAME).\n\n"
            "Étape 4 — Archivage :\n"
            f"Utilise l'outil 'archiver_fichier_drive' avec "
            f"source_folder_id='{FOLDER_DIFFUSION}', "
            f"archives_folder_id='{FOLDER_ARCHIVES}' et "
            "filename='ListeContacts_Lin_Out_FINAL' pour archiver le fichier "
            "Excel traité et éviter un double envoi. "
            "Le fichier 'ContenuMessage' reste dans le dossier (réutilisable)."
        ),
        expected_output=(
            "Rapport en quatre parties :\n"
            "1. Nombre de destinataires lus dans le fichier Excel.\n"
            "2. Objet et aperçu du corps du message lus dans ContenuMessage.\n"
            "3. Résultat de l'envoi : X email(s) envoyé(s) avec succès, Y échec(s).\n"
            "4. Confirmation de l'archivage du fichier Excel "
            "(ex. 'ListeContacts_Lin_Out_FINAL → ListeContacts_Lin_Out_FINAL_17062026')."
        ),
        agent=agent,
    )
