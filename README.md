# MINER — Système Multi-Agents IA de Prospection et Diffusion

> **Auteur** : Martial GADJEU | Data Engineer & AI

Système de **5 agents IA autonomes** construits avec **CrewAI** et un **LLM 100 % local (Ollama)**, capable d'extraire, consolider, nettoyer et diffuser une liste de contacts professionnels à partir de LinkedIn, Outlook et Google Sheets — **sans aucun coût de token, sans aucune donnée envoyée vers un service cloud d'IA**.

---

## Le défi : intelligence artificielle, prospection et confidentialité des données

La plupart des systèmes multi-agents actuels reposent sur des LLM hébergés dans le cloud (OpenAI, Claude, Gemini…). Pour des usages professionnels impliquant des **données de contact personnelles** (noms, adresses email, historique de messages), cette dépendance crée deux problèmes majeurs :

- **Confidentialité** : chaque appel API envoie vos données vers des serveurs tiers hors de votre contrôle.
- **Coût** : des milliers de contacts traités quotidiennement génèrent une facture de tokens significative.

**MINER répond à ces deux enjeux simultanément** : le moteur d'IA (Ollama + llama3.1) tourne entièrement sur la machine hôte. Aucune donnée de contact ne quitte votre infrastructure. Le coût marginal de traitement est **zéro**.

---

## Architecture

```
LinkedIn connections.csv ──► Agent 1 — Extracteur Connections ──►
LinkedIn messages.csv    ──► Agent 2 — Extracteur Messages    ──► Google Sheet
Boîte Outlook            ──► Agent 3 — Extracteur Outlook     ──► ListeContacts_Lin_Out
                                                                         │
                                                              [Export Excel manuel]
                                                                         │
                                                                         ▼
                                                               Agent 4 — Nettoyeur
                                                            (A verifier + Exclusions + Dédup)
                                                                         │
                                                                         ▼
                                                     Onglet ListeContacts_Lin_Out_FINAL
                                                                         │
                                                          [Export Excel → Drive manuel]
                                                                         │
                                                                         ▼
                                                          Agent 5 — Diffusion & Com
                                                     (Newsletters, campagnes, communications)
                                                                         │
                                                                         ▼
                                                               Envoi via Brevo API
```

---

## Les 5 agents

| # | Agent | Source / Déclencheur | Destination | Polling |
|---|---|---|---|---|
| 1 | **Extracteur Connections** | `connections.csv` dans Google Drive | Onglet `ListeContacts_Lin_Out` | 6 min |
| 2 | **Extracteur Messages** | `messages.csv` dans Google Drive | Onglet `ListeContacts_Lin_Out` | 8 min |
| 3 | **Extracteur Outlook** | Boîte Outlook (inbox + sentItems + Cc) | Onglet `ListeContacts_Lin_Out` | 5 min |
| 4 | **Nettoyeur** | Fichier Excel dans Drive `ListeContacts_Lin_Out_brute` | Onglet `ListeContacts_Lin_Out_FINAL` | 15 min |
| 5 | **Diffusion & Com** | Fichier Excel dans Drive `Diffusion_et_Communication` | Envoi email Brevo | 20 min |

### Agent 5 — Diffusion & Com en détail

L'Agent 5 est le bras armé de la communication sortante. À partir de la liste de prospects nettoyée, il est capable de diffuser :

- **Newsletters** — actualités, veille sectorielle, publications
- **Campagnes de prospection** — premiers contacts, relances
- **Communications internes ou partenariales** — invitations, annonces, rapports

Le message est rédigé dans un fichier `ContenuMessage.docx` (format `Objet: ...` + corps libre). L'agent lit le fichier, extrait l'objet et le corps, puis envoie un email individualisé à chaque destinataire via **Brevo** (ex-Sendinblue). Le fichier Excel des destinataires est archivé après envoi pour éviter les doublons.

---

## Pourquoi des agents en Python pur ?

Chaque agent est implémenté en **Python pur avec CrewAI**, sans framework d'abstraction supplémentaire. Ce choix offre :

- **Granularité totale** : chaque étape (extraction, déduplication, nettoyage, archivage) est une fonction Python testable et modifiable indépendamment.
- **Contrôle du flux de données** : aucune donnée ne transite par un intermédiaire opaque. Le code est lisible, auditable, déployable sur n'importe quelle infrastructure.
- **Extensibilité** : ajouter une nouvelle source de contacts (Salesforce, formulaire web, API tiers) = créer un outil Python + un crew. Aucune migration de plateforme nécessaire.
- **Stabilité** : les agents ne dépendent d'aucun service externe pour leur raisonnement. Ollama en local = pas de rate limit, pas de coupure API, pas de coût variable.

---

## Stack technique

| Composant | Technologie | Rôle |
|---|---|---|
| Orchestration agents | **CrewAI** | Coordination séquentielle, gestion des outils |
| LLM local | **Ollama + llama3.1** | Raisonnement des agents — 100 % local, coût zéro |
| Contacts LinkedIn | **Google Drive API v3** | Lecture des CSV exportés |
| Contacts Outlook | **Microsoft Graph API** | Lecture inbox + sentItems + Cc |
| Base de contacts | **Google Sheets API v4** | Stockage centralisé, déduplication |
| Diffusion email | **Brevo API** | Envoi transactionnel en masse |
| Déclenchement | **Polling Python** | Surveillance périodique sans webhooks |

---

## Sécurité et confidentialité

- **LLM 100 % local** : llama3.1 via Ollama tourne sur la machine hôte. Aucun nom, email ou contenu de message n'est envoyé vers OpenAI, Anthropic ou tout autre service cloud d'IA.
- **Coût zéro** : pas de facturation à l'usage, pas de quota, pas de clé API LLM. Seule la puissance de calcul locale est consommée.
- **Secrets isolés** : `.env` et `cles_google.json.json` sont dans `.gitignore` et ne sont jamais commités.
- **Principe de moindre privilège** : le compte de service Google n'a accès qu'aux dossiers Drive et Sheets explicitement partagés avec lui.
- **Données personnelles** : les contacts ne transitent que vers Google Drive/Sheets, Microsoft Graph et Brevo — jamais vers un tiers non maîtrisé.

---

## Structure du projet

```
Projet_MINER_agents_IA/
│
├── agents/                        # Définitions des 5 agents CrewAI
│   ├── agent_extracteur_linkedin_connections.py
│   ├── agent_extracteur_linkedin_messages.py
│   ├── agent_extracteur_outlook.py
│   ├── agent_nettoyeur.py
│   └── agent_diffusion_et_com.py
│
├── tools/                         # Outils utilisés par les agents (1 outil = 1 opération atomique)
│   ├── pipeline_tools.py          # Outils monolithiques — 1 appel LLM = pipeline complet
│   ├── google_drive_tools.py      # Lecture CSV/Excel, archivage Drive, extraction contacts
│   ├── google_sheets_tools.py     # Lecture/écriture/déduplication Google Sheets
│   ├── nettoyeur_tools.py         # Nettoyage en mémoire, écriture onglet FINAL
│   ├── outlook_tools.py           # Lecture boîte Outlook via Microsoft Graph API
│   └── diffusion_tools.py         # Lecture ContenuMessage.docx, envoi Brevo
│
├── tasks/                         # Définitions des tâches CrewAI
│   ├── tasks.py                   # Tâches agents 1 à 4
│   └── task_diffusion.py          # Tâche agent 5
│
├── systemd/                       # Services systemd pour déploiement VPS Ubuntu
│   ├── miner-main.service
│   ├── miner-diffusion.service
│   └── miner-exclusion.service
│
├── docs/                          # Documentation complète
│   ├── logique_projet.md          # Architecture, flux de données, guide développeur
│   └── DEPLOIEMENT_VPS.md         # Guide de déploiement sur VPS Linux
│
├── crew_connections.py            # Crew agent 1
├── crew_messages.py               # Crew agent 2
├── crew_outlook.py                # Crew agent 3
├── crew_nettoyeur.py              # Crew agent 4
├── crew_diffusion.py              # Crew agent 5
├── crew.py                        # Crew complet agents 1→4 (lancement séquentiel)
│
├── monitor_main.py                # Moniteur agents 1→4 (polling 6/8/5/15 min)
├── monitor_diffusion.py           # Moniteur agent 5 (polling 20 min)
├── monitor_exclusion.py           # Moniteur ListeExclusion (polling 10 min)
│
├── llm.py                         # Configuration LLM centralisée (Ollama)
├── main.py                        # Lancement manuel agents 1→4 en séquence
├── deploy.sh                      # Script de déploiement automatisé VPS
├── test_pipeline.py               # Diagnostic — teste chaque composant sans LLM
├── requirements.txt               # Dépendances Python
└── .env.example                   # Modèle de variables d'environnement
```

---

## Installation

### Prérequis

- Python 3.11+
- [Ollama](https://ollama.com) installé avec le modèle `llama3.1` téléchargé
- Compte de service Google avec accès Drive et Sheets
- Application Azure AD avec accès Microsoft Graph (pour Outlook)
- Compte Brevo avec clé API

### 1. Cloner et installer

```bash
git clone https://github.com/GuyMartial24/Syst-me-Multi-agents-IA-et-automatisation.git
cd Syst-me-Multi-agents-IA-et-automatisation
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

```env
# LLM local (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
OLLAMA_NUM_CTX=16384

# Google Cloud (compte de service)
GOOGLE_SERVICE_ACCOUNT_FILE=cles_google.json.json

# Microsoft Graph API (boîte Outlook)
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
ollama pull llama3.1
ollama serve    # ou via service système
```

---

## Utilisation

### Mode autonome (production)

```bash
python monitor_main.py       # Agents 1 à 4 — polling automatique
python monitor_diffusion.py  # Agent 5 — polling automatique
python monitor_exclusion.py  # Exclusions en temps réel
```

### Lancement manuel

```bash
python crew_connections.py   # Agent 1 — connections.csv
python crew_messages.py      # Agent 2 — messages.csv
python crew_outlook.py       # Agent 3 — Outlook
python crew_nettoyeur.py     # Agent 4 — nettoyage
python crew_diffusion.py     # Agent 5 — envoi email
```

### Diagnostic sans LLM

```bash
python test_pipeline.py      # Teste Sheets, Drive, Outlook, extraction CSV
```

---

## Format du fichier ContenuMessage.docx

```
Objet: Votre sujet d'email ici

Corps du message...
Ligne 2...
```

La ligne `Objet:` devient le sujet. Le reste constitue le corps envoyé à tous les destinataires.

---

## Documentation

- [Architecture et logique du projet](docs/logique_projet.md)
- [Guide de déploiement VPS](docs/DEPLOIEMENT_VPS.md)

---

*Martial GADJEU | Data Engineer & AI*
