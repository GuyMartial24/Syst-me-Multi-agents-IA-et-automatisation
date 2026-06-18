import json
import os
import requests
from crewai.tools import tool
from tools.google_drive_tools import _parse_prenom_nom, _extraire_domaine

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# Préfixes de la partie locale (avant @) correspondant à des expéditeurs automatiques :
# no-reply, newsletters, notifications système, marketing, etc.
_AUTO_PREFIXES = {
    "noreply", "no-reply", "no_reply",
    "nepasrepondre", "ne-pas-repondre", "ne_pas_repondre",
    "donotreply", "do-not-reply", "do_not_reply",
    "newsletter", "newsletters", "news", "mailing", "emailing",
    "notification", "notifications", "notify",
    "alert", "alerts", "update", "updates",
    "mailer", "mailer-daemon", "postmaster",
    "bounce", "bounces", "automated", "robot", "system",
    "admin", "support", "contact",
    "marketing",
}


def _est_adresse_automatique(email: str) -> bool:
    """Retourne True si l'adresse correspond à un expéditeur automatique."""
    local = email.split("@")[0].lower()
    return local in _AUTO_PREFIXES


def _get_access_token() -> str:
    tenant_id = os.environ["OUTLOOK_OAUTH_TENANT_ID"]
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id":     os.environ["OUTLOOK_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["OUTLOOK_OAUTH_CLIENT_SECRET"],
        "scope":         "https://graph.microsoft.com/.default",
        "grant_type":    "client_credentials",
    }
    resp = requests.post(url, data=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _fetch_messages(token: str, mailbox: str, folder: str, top: int, since_dt: str = "") -> list:
    """
    Récupère les messages d'un dossier Outlook (inbox ou sentitems).
    Si since_dt est fourni (format ISO 8601 UTC, ex. '2026-06-18T08:00:00Z'),
    seuls les messages reçus/envoyés après cette date sont retournés.
    """
    headers = {"Authorization": f"Bearer {token}"}

    date_field = "sentDateTime" if folder == "sentitems" else "receivedDateTime"
    filter_clause = f"&$filter={date_field} gt {since_dt}" if since_dt else ""

    url = (
        f"{GRAPH_API_BASE}/users/{mailbox}/mailFolders/{folder}/messages"
        f"?$top={top}&$select=from,toRecipients,ccRecipients{filter_clause}"
    )
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("value", [])


@tool("Lire les emails de la boîte Outlook de Pierre Bono")
def lire_emails_outlook(top_par_dossier: int = 100) -> str:
    """
    Récupère les contacts des emails entrants (inbox) et sortants (sentitems)
    de la boîte Outlook de Pierre Bono via Microsoft Graph API.

    Pour chaque message, extrait les adresses FROM, TO et CC.
    Exclut Pierre Bono (propriétaire de la boîte).

    Retourne une liste JSON de contacts formatés pour le Google Sheet :
    Email (minuscules), Prenom (1ère lettre majuscule), Nom (MAJUSCULES),
    Source='Outlook', A_verifier='' (vide), Domaine, Statut='' (vide), Extension.
    Seuls les contacts avec une adresse email valide sont inclus.
    """
    try:
        mailbox = os.environ["OUTLOOK_TARGET_MAILBOX"]
        mailbox_lower = mailbox.strip().lower()
        token = _get_access_token()
    except Exception as exc:
        return json.dumps({"erreur": f"Authentification Outlook impossible : {exc}"})

    # Si le monitor a défini OUTLOOK_SINCE_DT, on ne récupère que les nouveaux messages.
    # Sinon, on récupère les N derniers (mode manuel / premier lancement).
    since_dt = os.environ.get("OUTLOOK_SINCE_DT", "")

    try:
        messages = (
            _fetch_messages(token, mailbox, "inbox",     top_par_dossier, since_dt) +
            _fetch_messages(token, mailbox, "sentitems", top_par_dossier, since_dt)
        )
    except Exception as exc:
        return json.dumps({"erreur": f"Erreur lecture boîte Outlook : {exc}"})

    contacts: dict[str, dict] = {}

    for msg in messages:
        # Collecter toutes les adresses du message (From + To + Cc)
        adresses = []
        if msg.get("from", {}).get("emailAddress"):
            adresses.append(msg["from"]["emailAddress"])
        adresses += [r["emailAddress"] for r in msg.get("toRecipients", [])]
        adresses += [r["emailAddress"] for r in msg.get("ccRecipients",  [])]

        for adr in adresses:
            email = adr.get("address", "").strip().lower()

            # Règles d'exclusion
            if not email or "@" not in email:
                continue
            if email == mailbox_lower:              # exclure Pierre Bono
                continue
            if _est_adresse_automatique(email):     # exclure no-reply, newsletters, etc.
                continue
            if email in contacts:                   # déjà traité
                continue

            name = adr.get("name", "").strip()
            prenom, nom = _parse_prenom_nom(name)
            domaine, extension = _extraire_domaine(email)

            contacts[email] = {
                "Email":      email,
                "Prenom":     prenom,
                "Nom":        nom,
                "Source":     "Outlook",
                "A_verifier": "",
                "Domaine":    domaine,
                "Statut":     "",
                "Extension":  extension,
            }

    return json.dumps(list(contacts.values()), ensure_ascii=False, indent=2)
