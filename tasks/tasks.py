from crewai import Task, Agent

# IDs des dossiers Google Drive
FOLDER_LINKEDIN_CONNECTIONS = "1X_IDqTFPg-Hh-jkRnyTBnDjVmaXtgF_1"
FOLDER_LINKEDIN_MESSAGES    = "1Qd9yDA2N4kHSovlGA8aZavlAbQ3yeI2b"
FOLDER_LISTE_BRUTE          = "1JCQvWRjGHH01wzgQDhVK9ho57xszIlI4"
FOLDER_LISTE_FINALE         = "1JjFDdTs2yt-fp2j795i2TUxI9fuKkGUG"
FOLDER_ARCHIVES             = "1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh"


def create_task_extraction_connections(agent: Agent) -> Task:
    return Task(
        description=(
            f"Étape 1 — Extraction :\n"
            f"Utilise l'outil 'extraire_contacts_connections' avec le folder_id "
            f"'{FOLDER_LINKEDIN_CONNECTIONS}' pour lire et formater les contacts "
            f"du fichier connections.csv.\n"
            "Chaque contact doit être formaté avec les colonnes exactes :\n"
            "  • Email       : adresse email en minuscules\n"
            "  • Prenom      : première lettre en majuscule (ex. Jean)\n"
            "  • Nom         : entièrement en MAJUSCULES (ex. DUPONT)\n"
            "  • Source      : valeur fixe 'Linkedin'\n"
            "  • A_verifier  : laisser VIDE — ne pas remplir\n"
            "  • Domaine     : domaine extrait de l'email (ex. gmail.com)\n"
            "  • Statut      : laisser VIDE — ne pas remplir\n"
            "  • Extension   : extension du domaine (ex. .com)\n"
            "Seuls les contacts avec une adresse email valide sont inclus.\n"
            "Utilise l'outil 'ecrire_contacts_sans_doublons' pour écrire "
            "les contacts dans l'onglet 'ListeContacts_Lin_connexions'.\n\n"
            f"Étape 2 — Archivage :\n"
            f"Une fois l'écriture confirmée, utilise l'outil 'archiver_fichier_drive' "
            f"avec source_folder_id='{FOLDER_LINKEDIN_CONNECTIONS}', "
            f"archives_folder_id='{FOLDER_ARCHIVES}' et filename='connections.csv'. "
            "Le fichier sera renommé avec la date du jour (ex. connections_17062026.csv) "
            "et déplacé dans Archives. Le dossier source doit être vide après cette étape.\n"
            "EXIGENCE CRITIQUE : chaque étape doit être réalisée en déclenchant RÉELLEMENT "
            "l'outil Python correspondant. Ne jamais décrire ou simuler un appel d'outil — "
            "déclencher l'outil directement et restituer sa sortie brute."
        ),
        expected_output=(
            "Sortie brute des outils, sans prose ni commentaire :\n"
            "1. Résultat de ecrire_contacts_sans_doublons : 'X contact(s) ajouté(s) dans "
            "ListeContacts_Lin_connexions. Y ignoré(s) car déjà présent(s).'\n"
            "2. Résultat de archiver_fichier_drive : 'connections.csv → connections_JJMMAAAA.csv'"
        ),
        agent=agent,
    )


def create_task_extraction_messages(agent: Agent) -> Task:
    return Task(
        description=(
            f"Étape 1 — Extraction :\n"
            f"Utilise l'outil 'extraire_contacts_messages' avec le folder_id "
            f"'{FOLDER_LINKEDIN_MESSAGES}' pour lire et formater les contacts "
            f"du fichier messages.csv.\n"
            "Règles d'extraction :\n"
            "  • Contacts identifiés dans les colonnes FROM et TO.\n"
            "  • Exclure 'Pierre BONO' (propriétaire) et 'LinkedIn Member' (sponsorisés).\n"
            "  • Si un email est trouvé dans le CONTENT d'un message FROM ce contact, l'associer.\n"
            "  • Contacts sans email : exclus (Email obligatoire).\n"
            "Colonnes : Email, Prenom, Nom, Source='Linkedin', A_verifier='', "
            "Domaine, Statut='', Extension.\n"
            "Utilise l'outil 'ecrire_contacts_sans_doublons' pour écrire "
            "les contacts dans l'onglet 'ListeContacts_Lin_messages'.\n\n"
            f"Étape 2 — Archivage :\n"
            f"Une fois l'écriture confirmée, utilise l'outil 'archiver_fichier_drive' "
            f"avec source_folder_id='{FOLDER_LINKEDIN_MESSAGES}', "
            f"archives_folder_id='{FOLDER_ARCHIVES}' et filename='messages.csv'. "
            "Le fichier sera renommé avec la date du jour (ex. messages_17062026.csv) "
            "et déplacé dans Archives. Le dossier source doit être vide après cette étape.\n"
            "EXIGENCE CRITIQUE : chaque étape doit être réalisée en déclenchant RÉELLEMENT "
            "l'outil Python correspondant. Ne jamais décrire ou simuler un appel d'outil — "
            "déclencher l'outil directement et restituer sa sortie brute."
        ),
        expected_output=(
            "Sortie brute des outils, sans prose ni commentaire :\n"
            "1. Résultat de ecrire_contacts_sans_doublons : 'X contact(s) ajouté(s) dans "
            "ListeContacts_Lin_messages. Y ignoré(s) car déjà présent(s).'\n"
            "2. Résultat de archiver_fichier_drive : 'messages.csv → messages_JJMMAAAA.csv'"
        ),
        agent=agent,
    )


def create_task_extraction_outlook(agent: Agent) -> Task:
    return Task(
        description=(
            "Utilise l'outil 'lire_emails_outlook' pour récupérer les contacts "
            "des emails entrants (Inbox) ET sortants (SentItems) de Pierre Bono.\n"
            "Pour chaque message, les adresses From, To et Cc sont extraites.\n"
            "Pierre Bono (pierre.bono@f-r-d.fr) est exclu automatiquement.\n"
            "Chaque contact est formaté avec les colonnes exactes :\n"
            "  • Email       : adresse email en minuscules\n"
            "  • Prenom      : première lettre en majuscule (ex. Xavier)\n"
            "  • Nom         : entièrement en MAJUSCULES (ex. DREUX)\n"
            "  • Source      : valeur fixe 'Outlook'\n"
            "  • A_verifier  : laisser VIDE — ne pas remplir\n"
            "  • Domaine     : domaine extrait de l'email (ex. f-r-d.fr)\n"
            "  • Statut      : laisser VIDE — ne pas remplir\n"
            "  • Extension   : extension du domaine (ex. .fr)\n"
            "Utilise l'outil 'ecrire_contacts_sans_doublons' pour écrire "
            "les contacts dans l'onglet 'ListeContacts_Out'. "
            "Si un contact existe déjà (même email), conserver la version existante.\n"
            "EXIGENCE CRITIQUE : chaque étape doit être réalisée en déclenchant RÉELLEMENT "
            "l'outil Python correspondant. Ne jamais décrire ou simuler un appel d'outil — "
            "déclencher l'outil directement et restituer sa sortie brute."
        ),
        expected_output=(
            "Sortie brute de l'outil ecrire_contacts_sans_doublons, sans prose ni commentaire. "
            "Exemple exact attendu : 'X contact(s) ajouté(s) dans ListeContacts_Out. "
            "Y ignoré(s) car déjà présent(s) (version existante conservée).'"
        ),
        agent=agent,
    )


def create_task_nettoyage(agent: Agent, context: list) -> Task:
    return Task(
        description=(
            "Étape 1 — Suppression des lignes 'A vérifier' = 1 :\n"
            "Utilise l'outil 'supprimer_lignes_a_verifier' sur l'onglet "
            "'ListeContacts_Lin_Out_FINAL' pour supprimer toutes les lignes "
            "dont la colonne 'A vérifier' vaut 1.\n\n"
            "Étape 2 — Suppression des emails exclus :\n"
            "Utilise l'outil 'supprimer_emails_exclus' sur l'onglet "
            "'ListeContacts_Lin_Out_FINAL' pour supprimer toutes les lignes "
            "dont l'adresse email figure dans le fichier ListeExclusion "
            "(ID : 1sz7xUM05y6xI-bj1Wz8jvmOzuIH7ZzCoEyECgqkZ9xc, "
            "colonne 'Emails exclus').\n\n"
            "Étape 3 — Dédoublonnage :\n"
            "Utilise l'outil 'dedoublonner_google_sheet' sur l'onglet "
            "'ListeContacts_Lin_Out_FINAL' pour supprimer les doublons "
            "sur la colonne 'Email'.\n\n"
            f"Étape 4 — Archivage :\n"
            f"Utilise l'outil 'archiver_fichier_drive' avec "
            f"source_folder_id='{FOLDER_LISTE_BRUTE}' et "
            f"archives_folder_id='{FOLDER_ARCHIVES}' (sans préciser filename pour "
            "archiver tous les fichiers présents). "
            "Chaque fichier sera renommé avec la date du jour et déplacé dans Archives. "
            "Le dossier ListeContacts_Lin_Out_brute doit être vide après cette étape.\n"
            "EXIGENCE CRITIQUE : chaque étape doit être réalisée en déclenchant RÉELLEMENT "
            "l'outil Python correspondant. Ne jamais décrire ou simuler un appel d'outil — "
            "déclencher l'outil directement et restituer sa sortie brute."
        ),
        expected_output=(
            "Sortie brute des 4 outils exécutés, sans prose ni commentaire :\n"
            "1. Résultat de supprimer_lignes_a_verifier.\n"
            "2. Résultat de supprimer_emails_exclus.\n"
            "3. Résultat de dedoublonner_google_sheet.\n"
            "4. Résultat de archiver_fichier_drive."
        ),
        agent=agent,
        context=context,
    )
