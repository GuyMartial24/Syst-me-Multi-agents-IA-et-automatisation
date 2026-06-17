# MINER — Système Multi-Agents IA d'Automatisation de Contacts

Système de 5 agents IA autonomes construits avec **CrewAI**, capables d'extraire, nettoyer et diffuser une liste de contacts professionnels à partir de LinkedIn, Outlook et Google Sheets, via une orchestration entièrement automatisée.

---

## Architecture

```
LinkedIn connections.csv ──► Agent 1 (Extracteur Connections) ──►
LinkedIn messages.csv    ──► Agent 2 (Extracteur Messages)    ──► Google Sheet
Boîte Outlook            ──► Agent 3 (Extracteur Outlook)     ──►      │
                                                                         ▼
                                                               Agent 4 (Nettoyeur)
                                                                         │
                                                                         ▼
                                                          Agent 5 (Diffusion & Com)
                                                                         │
                                                                         ▼
                                                               Envoi via Brevo API
```

### Les 5 agents

| Agent | Source | Onglet Google Sheet | Archivage |
|---|---|---|---|
| Extracteur Connections | `connections.csv` (Google Drive) | `ListeContacts_Lin_connexions` | Oui |
| Extracteur Messages | `messages.csv` (Google Drive) | `ListeContacts_Lin_messages` | Oui |
| Extracteur Outlook | Boîte Outlook via Microsoft Graph API | `ListeContacts_Out` | — |
| Nettoyeur | Google Sheet principal | `ListeContacts_Lin_Out_FINAL` | Oui |
| Diffusion & Com | Fichier Excel Drive + ContenuMessage.docx | — (envoi email) | Oui |

---

## Stack technique

- **[CrewAI](https://github.com/crewAIInc/crewAI)** — orchestration multi-agents
- **[Ollama](https://ollama.com)** + `deepseek-r1:8b` — LLM local (aucun envoi de données vers le cloud)
- **Google Drive API** + **Google Sheets API v4** — stockage et lecture des données
- **Microsoft Graph API** — accès à la boîte Outlook (client credentials flow)
- **Brevo (ex-Sendinblue)** — diffusion email transactionnelle

---

## Structure du projet

```
Projet_MINER_agents_IA/
├── agents/
│   ├── agent_extracteur_linkedin_connections.py
│   ├── agent_extracteur_linkedin_messages.py
│   ├── agent_extracteur_outlook.py
│   ├── agent_nettoyeur.py
│   └── agent_diffusion_et_com.py
├── tools/
│   ├── google_drive_tools.py      # Lecture CSV, archivage Drive
│   ├── google_sheets_tools.py     # Lecture/écriture/dédup Google Sheets
│   ├── outlook_tools.py           # Lecture boîte Outlook via Graph API
│   └── diffusion_tools.py        # Lecture ContenuMessage, envoi Brevo
├── tasks/
│   ├── tasks.py                   # Tâches agents 1→4
│   └── task_diffusion.py          # Tâche agent 5
├── crew.py                        # Crew principal (agents 1→4)
├── crew_diffusion.py              # Crew diffusion (agent 5)
├── monitor_exclusion.py           # Surveillance ListeExclusion (polling 10 min)
├── monitor_diffusion.py           # Surveillance dossier Diffusion (polling 20 min)
├── llm.py                         # Configuration LLM partagée (Ollama)
├── main.py                        # Point d'entrée principal
├── requirements.txt
└── .env.example                   # Variables d'environnement requises
```

---

## Règles métier

### Google Sheet principal (`ListeContacts_Lin_Out_FINAL`)
- Colonnes fixes (A→I) : `Email`, `Prenom`, `Nom`, `Source`, `A_verifier`, `Domaine`, `Statut`, `Extension`, `Date_insertion`
- **Email obligatoire** — toute ligne sans email est rejetée
- **Déduplication** sur la colonne `Email` (insensible à la casse) — la version existante est conservée
- **Date d'insertion** au format `jj/mm/aaaa`, ajoutée automatiquement à l'écriture
- **Archivage** : après chaque opération, le fichier source est renommé `nom_jjmmaaaa.ext` et déplacé dans le dossier `Archives`

### Agent Nettoyeur
Trois passes successives sur `ListeContacts_Lin_Out_FINAL` :
1. Suppression des lignes `A_verifier = 1`
2. Suppression des emails présents dans **ListeExclusion** (Google Sheet séparé, colonne `Emails exclus`)
3. Déduplication sur `Email`

### Monitor ListeExclusion (`monitor_exclusion.py`)
Surveillance continue (toutes les **10 minutes**) — dès qu'une nouvelle adresse est ajoutée à ListeExclusion, elle est immédiatement supprimée de `ListeContacts_Lin_Out_FINAL`.

### Agent Diffusion & Com
- Détecté via `monitor_diffusion.py` (polling **20 minutes**) sur le dossier Drive `Diffusion_et_Communication`
- Lit `ContenuMessage.docx` : ligne `Objet: ...` → sujet de l'email, reste → corps
- Envoie un email identique à tous les contacts via l'API Brevo
- Archive le fichier Excel après envoi pour éviter les doublons

---

## Installation

### Prérequis
- Python 3.11+
- [Ollama](https://ollama.com) installé et modèle `deepseek-r1:8b` téléchargé
- Compte de service Google avec accès Drive et Sheets
- Application Azure AD avec accès Microsoft Graph (pour Outlook)
- Compte Brevo avec clé API

### 1. Cloner et installer

```bash
git clone https://github.com/GuyMartial24/Syst-me-Multi-agents-IA-et-automatisation.git
cd Syst-me-Multi-agents-IA-et-automatisation
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Renseigner dans `.env` :

```env
# LLM local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
OLLAMA_NUM_CTX=16384

# Google (fichier de clés du compte de service)
GOOGLE_SERVICE_ACCOUNT_FILE=cles_google.json.json

# Microsoft Graph (Outlook)
OUTLOOK_OAUTH_CLIENT_ID=...
OUTLOOK_OAUTH_TENANT_ID=...
OUTLOOK_OAUTH_CLIENT_SECRET=...
OUTLOOK_TARGET_MAILBOX=prenom.nom@domaine.fr

# Brevo / Sendinblue (diffusion email)
SENDINBLUE_API_KEY=...
SENDINBLUE_SENDER_EMAIL=...
SENDINBLUE_SENDER_NAME=...
```

### 3. Lancer Ollama

```bash
ollama run deepseek-r1:8b
```

---

## Utilisation

### Lancer le crew principal (extraction + nettoyage)

```bash
python crew.py
```

### Lancer le crew de diffusion manuellement

```bash
python crew_diffusion.py
```

### Lancer les monitors en arrière-plan

```bash
# Surveillance ListeExclusion (10 min)
python monitor_exclusion.py

# Surveillance dossier Diffusion (20 min)
python monitor_diffusion.py
```

---

## Format du fichier ContenuMessage.docx

```
Objet: Votre sujet d'email ici

Corps du message ici...
Ligne 2...
Ligne 3...
```

La ligne commençant par `Objet:` est extraite comme sujet de l'email. Le reste constitue le corps.

---

## Sécurité

- Le fichier `cles_google.json.json` (credentials Google) ne doit **jamais** être commité — il est dans `.gitignore`
- Le fichier `.env` contient les secrets — il est dans `.gitignore`
- Le LLM tourne **en local** via Ollama : aucune donnée de contact n'est envoyée vers un service cloud d'IA
