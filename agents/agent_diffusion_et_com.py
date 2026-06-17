from crewai import Agent
from langchain_ollama import ChatOllama
from tools.diffusion_tools import (
    lire_contenu_message_depuis_drive,
    lire_emails_depuis_excel_drive,
    envoyer_emails_via_sendinblue,
)
from tools.google_drive_tools import archiver_fichier_drive


def create_agent_diffusion_et_com(llm: ChatOllama) -> Agent:
    """
    Agent 5 — Diffusion_et_Com
    Déclenché par la présence d'un fichier Excel 'ListeContacts_Lin_Out_FINAL'
    dans le dossier Drive 'Diffusion_et_Communication'.
    Lit le contenu du message (ContenuMessage) dans ce même dossier,
    envoie un email identique à chaque contact via l'API Sendinblue (Brevo),
    puis archive le fichier Excel dans le dossier Archives.
    """
    return Agent(
        role="Chargé de diffusion et communication par email",
        goal=(
            "Lire la liste des contacts (fichier Excel 'ListeContacts_Lin_Out_FINAL') "
            "depuis le dossier Google Drive 'Diffusion_et_Communication', "
            "et le contenu du message (fichier 'ContenuMessage.docx', ID fixe Drive), "
            "puis envoyer un email identique à chaque adresse email de la liste "
            "via l'API Sendinblue (Brevo). "
            "L'objet du message est extrait directement du fichier ContenuMessage "
            "(ligne commençant par 'Objet:'). "
            "Les paramètres d'expéditeur sont configurés dans les variables "
            "d'environnement (SENDINBLUE_SENDER_EMAIL, SENDINBLUE_SENDER_NAME). "
            "Après envoi, archiver le fichier Excel dans le dossier Archives."
        ),
        backstory=(
            "Agent spécialisé dans la diffusion de messages professionnels. "
            "Tu extrais les destinataires d'un fichier Excel, lis le contenu d'un message "
            "depuis Google Drive (format .docx), et utilises l'API Brevo "
            "pour envoyer un email identique à chaque contact. "
            "Tu archives systématiquement les fichiers traités pour éviter les doublons d'envoi."
        ),
        tools=[
            lire_emails_depuis_excel_drive,
            lire_contenu_message_depuis_drive,
            envoyer_emails_via_sendinblue,
            archiver_fichier_drive,
        ],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
