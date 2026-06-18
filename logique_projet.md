# MINER — Documentation complète du projet

## Sommaire

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture technique](#2-architecture-technique)
3. [Dossiers et fichiers Google Drive](#3-dossiers-et-fichiers-google-drive)
4. [Feuilles Google Sheets](#4-feuilles-google-sheets)
5. [Les 5 agents IA](#5-les-5-agents-ia)
6. [Les moniteurs de surveillance](#6-les-moniteurs-de-surveillance)
7. [Mode opératoire — Guide utilisateur](#7-mode-opératoire--guide-utilisateur)
8. [Structure des fichiers du projet](#8-structure-des-fichiers-du-projet)
9. [Variables d'environnement](#9-variables-denvironnement)
10. [Guide développeur](#10-guide-développeur)
11. [Sécurité](#11-sécurité)

---

## 1. Vue d'ensemble

**MINER** est un système multi-agents IA entièrement automatisé dont le but est de **construire et maintenir une liste de contacts professionnels**, puis de **diffuser des messages email** à cette liste.

Le système extrait les contacts depuis trois sources :
- Les **connexions LinkedIn** de l'utilisateur (fichier `connections.csv`)
- Les **messages LinkedIn** échangés (fichier `messages.csv`)
- La **boîte email Outlook** de Pierre Bono (via Microsoft Graph API)

Ces contacts sont centralisés dans un **Google Sheet**, nettoyés, dédoublonnés, filtrés par une liste d'exclusion, puis mis à disposition pour une campagne d'envoi email.

Toutes les opérations sont **déclenchées automatiquement** par des moniteurs de surveillance qui tournent en permanence en arrière-plan. Aucune action manuelle n'est nécessaire en fonctionnement normal.

### Principe de confidentialité des données

Le moteur d'intelligence artificielle est **local** (Ollama sur la machine hôte). Aucune donnée personnelle (noms, adresses email) n'est envoyée à un service cloud d'IA. Seules les API Google, Microsoft et Brevo reçoivent les données nécessaires à leur fonctionnement propre.

---

## 2. Architecture technique

### Technologies utilisées

| Composant | Technologie | Rôle |
|---|---|---|
| Orchestration des agents | **CrewAI** | Coordination séquentielle des tâches |
| Modèle de langage | **Ollama — deepseek-r1:8b** | LLM local, raisonnement des agents |
| Contacts LinkedIn | **Google Drive API v3** | Lecture des CSV exportés depuis LinkedIn |
| Contacts Outlook | **Microsoft Graph API** | Lecture des emails entrants et sortants |
| Stockage des contacts | **Google Sheets API v4** | Base de données centrale des contacts |
| Diffusion email | **Brevo (ex-Sendinblue) API** | Envoi des emails en masse |
| Triggers automatiques | **Polling** (scripts Python) | Surveillance périodique sans webhooks |

### Vue globale du flux de données

```
LinkedIn connections.csv ──────┐
LinkedIn messages.csv  ─────── ├──► Google Sheet (ListeContacts_*) ──► Nettoyage ──► ListeContacts_Lin_Out_FINAL
Outlook (inbox + sentItems) ───┘                                                              │
                                                                                              ▼
ListeExclusion (Google Sheet) ──────────────────────────────────────────────────► Suppression en temps réel
                                                                                              │
                                                                                              ▼
                                                                    Dossier Drive Diffusion ──► Envoi email (Brevo)
```

### Processus de déclenchement automatique

Le système ne repose pas sur des webhooks (pas d'URL publique disponible sur une machine locale). Il utilise à la place un **mécanisme de polling** : des scripts Python tournent en permanence et interrogent les APIs à intervalles réguliers pour détecter des changements.

---

## 3. Dossiers et fichiers Google Drive

### Vue d'ensemble des dossiers

Tous les dossiers suivants sont dans le Google Drive du compte de service. Le compte de service doit avoir les droits **Éditeur** sur chacun d'eux.

### Dossiers de sources LinkedIn

**Dossier : `Linkedin_connections`**
- ID Drive : `1X_IDqTFPg-Hh-jkRnyTBnDjVmaXtgF_1`
- Contenu attendu : le fichier `connections.csv` exporté depuis LinkedIn
- Surveillance : toutes les **15 minutes** par `monitor_main.py`
- Après traitement : le fichier est renommé `connections_jjmmaaaa.csv` et déplacé dans Archives

**Dossier : `Linkedin_messages`**
- ID Drive : `1Qd9yDA2N4kHSovlGA8aZavlAbQ3yeI2b`
- Contenu attendu : le fichier `messages.csv` exporté depuis LinkedIn
- Surveillance : toutes les **15 minutes** par `monitor_main.py`
- Après traitement : le fichier est renommé `messages_jjmmaaaa.csv` et déplacé dans Archives

### Dossier intermédiaire

**Dossier : `ListeContacts_Lin_Out_brute`**
- ID Drive : `1JCQvWRjGHH01wzgQDhVK9ho57xszIlI4`
- Rôle : dossier déclencheur pour l'agent Nettoyeur
- Contenu : tout fichier présent dans ce dossier déclenche le nettoyage
- Surveillance : toutes les **15 minutes** par `monitor_main.py`
- Après traitement : le fichier est archivé avec la date dans le nom

### Dossier de la liste finale

**Dossier : `ListeFinale`**
- ID Drive : `1JjFDdTs2yt-fp2j795i2TUxI9fuKkGUG`
- Rôle : référence uniquement (non surveillé directement)

### Dossier de diffusion

**Dossier : `Diffusion_et_Communication`**
- ID Drive : `1peQ9728pAY2h2j60i-Wns4-bXyjZzVzl`
- Surveillance : toutes les **20 minutes** par `monitor_diffusion.py`
- Contenu attendu :
  - `ListeContacts_Lin_Out_FINAL` — fichier Excel sans extension (format `.xlsx`) contenant les contacts à contacter, avec une colonne `Email`
  - `ContenuMessage.docx` (ID fixe : `14V2EpnEaO4EW4AHKmNGM6w2An-GWrYhn`) — fichier Word contenant l'objet et le corps de l'email à envoyer
- Après traitement : `ListeContacts_Lin_Out_FINAL` est renommé avec la date et déplacé dans Archives. `ContenuMessage.docx` **reste en place** (réutilisable pour d'autres campagnes)

### Dossier d'archives

**Dossier : `Archives`**
- ID Drive : `1zvizg72FmeVF1nB2o5jKYPIvH9vxOblh`
- Rôle : stockage des fichiers traités
- Convention de nommage : `nom_original_jjmmaaaa.ext` (ex. `connections_18062026.csv`)
- Les fichiers sans extension reçoivent un suffixe sans point : `ListeContacts_Lin_Out_FINAL_18062026`

### Fichier ContenuMessage.docx — Format attendu

Le fichier doit respecter impérativement cette convention :

```
Objet: [Titre de votre email]

[Corps du message, sur autant de lignes que nécessaire.]
```

- La première ligne commençant par `Objet:` devient le sujet de l'email.
- Tout le texte suivant devient le corps du message.
- Si aucune ligne `Objet:` n'est trouvée, la première ligne est utilisée comme sujet.
- Le message est envoyé **identique** à tous les destinataires, sans personnalisation.

---

## 4. Feuilles Google Sheets

### Google Sheet principal — ListeContacts

- **ID** : `1yEWVIlazcfih3iymhICk3pY2jXwVAisgeZB8WVje8a0`
- Contient plusieurs onglets selon la source des contacts

#### Structure des colonnes (identique pour tous les onglets)

| Colonne | Nom | Description | Valeurs possibles |
|---|---|---|---|
| A | `Email` | Adresse email (obligatoire) | Minuscules, ex. `jean.dupont@gmail.com` |
| B | `Prenom` | Prénom | Première lettre majuscule, ex. `Jean` |
| C | `Nom` | Nom de famille | Tout en majuscules, ex. `DUPONT` |
| D | `Source` | Origine du contact | `Linkedin` ou `Outlook` |
| E | `A_verifier` | Indicateur de vérification manuelle | `1` = à supprimer, vide = OK |
| F | `Domaine` | Domaine de l'adresse email | ex. `gmail.com` |
| G | `Statut` | Statut libre (non rempli par les agents) | Vide par défaut |
| H | `Extension` | Extension du domaine | ex. `.com`, `.fr` |
| I | `Date_insertion` | Date d'insertion automatique | Format `jj/mm/aaaa` |

**Règle absolue** : toute ligne sans adresse email est rejetée avant insertion.

**Règle de déduplication** : si un email existe déjà dans l'onglet, la ligne entrante est ignorée et la version existante est conservée.

#### Onglets du Google Sheet principal

| Onglet | Alimenté par | Description |
|---|---|---|
| `ListeContacts_Lin_connexions` | Agent 1 | Contacts extraits de `connections.csv` |
| `ListeContacts_Lin_messages` | Agent 2 | Contacts extraits de `messages.csv` |
| `ListeContacts_Out` | Agent 3 | Contacts extraits de la boîte Outlook |
| `ListeContacts_Lin_Out_FINAL` | Agent 4 + Monitor Exclusion | Liste finale nettoyée, prête pour diffusion |

### Google Sheet ListeExclusion

- **ID** : `1sz7xUM05y6xI-bj1Wz8jvmOzuIH7ZzCoEyECgqkZ9xc`
- Onglet unique, colonne A, en-tête `Emails exclus`
- Toute adresse email saisie dans cette liste est **immédiatement supprimée** de `ListeContacts_Lin_Out_FINAL` (dans les 10 minutes)
- L'agent Nettoyeur consulte également cette liste à chaque exécution

---

## 5. Les 5 agents IA

Chaque agent est une instance CrewAI dotée d'un rôle, d'un objectif et d'un ensemble d'outils. Le LLM local (deepseek-r1:8b via Ollama) orchestre l'utilisation des outils pour accomplir les tâches.

---

### Agent 1 — Extracteur LinkedIn Connections

**Fichier** : `agents/agent_extracteur_linkedin.py`
**Crew** : `crew_connections.py`
**Trigger** : présence de `connections.csv` dans le dossier `Linkedin_connections`

**Ce que fait cet agent :**
1. Télécharge `connections.csv` depuis Google Drive
2. Détecte dynamiquement l'en-tête (le fichier LinkedIn comporte des lignes de notes avant les vraies données)
3. Pour chaque ligne : extrait Email, First Name, Last Name ; ignore les lignes sans email
4. Formate les contacts : email en minuscules, prénom avec majuscule initiale, nom en MAJUSCULES, Source=`Linkedin`
5. Écrit les contacts dans l'onglet `ListeContacts_Lin_connexions` sans créer de doublons
6. Archive `connections.csv` dans le dossier Archives (renommé avec la date)

**Outils utilisés** :
- `extraire_contacts_connections` — télécharge et parse le CSV
- `ecrire_contacts_sans_doublons` — insère dans Google Sheets
- `archiver_fichier_drive` — déplace le fichier traité vers Archives

---

### Agent 2 — Extracteur LinkedIn Messages

**Fichier** : `agents/agent_extracteur_linkedin.py`
**Crew** : `crew_messages.py`
**Trigger** : présence de `messages.csv` dans le dossier `Linkedin_messages`

**Ce que fait cet agent :**
1. Télécharge `messages.csv` depuis Google Drive
2. Détecte dynamiquement l'en-tête (cherche la ligne contenant `CONVERSATION ID`)
3. Pour chaque message, inspecte les colonnes `FROM` et `TO`
4. Exclut automatiquement :
   - Pierre BONO (propriétaire du compte LinkedIn)
   - Les profils `LinkedIn Member` (membres anonymes de campagnes sponsorisées)
5. Déduplique par URL de profil LinkedIn (clé plus fiable que le nom)
6. Cherche les emails dans le `CONTENT` des messages : si un expéditeur a inclus son email dans le corps d'un message, il est associé à ce contact
7. N'insère que les contacts disposant d'un email valide
8. Archive `messages.csv` dans Archives

**Particularité** : les contacts LinkedIn issus des messages n'ont souvent pas d'email dans les colonnes standard. L'agent tente de l'extraire du contenu textuel des échanges. Les contacts sans email sont silencieusement ignorés.

**Outils utilisés** :
- `extraire_contacts_messages`
- `ecrire_contacts_sans_doublons`
- `archiver_fichier_drive`

---

### Agent 3 — Extracteur Outlook

**Fichier** : `agents/agent_extracteur_outlook.py`
**Crew** : `crew_outlook.py`
**Trigger** : nouveaux emails dans la boîte Outlook de Pierre Bono (polling Microsoft Graph API toutes les 30 minutes)

**Ce que fait cet agent :**
1. S'authentifie sur Microsoft Graph API via OAuth2 (flux client credentials)
2. Récupère les messages de `inbox` ET `sentItems` de Pierre Bono
3. Pour chaque message, extrait **toutes** les adresses impliquées : `From`, `To`, `Cc`
4. Exclut automatiquement Pierre Bono (propriétaire de la boîte)
5. Exclut les adresses **automatiques** (no-reply, newsletters, notifications) :
   - Préfixes exclus : `noreply`, `no-reply`, `newsletter`, `notification`, `alert`, `mailer`, `postmaster`, `bounce`, `automated`, `robot`, `system`, `admin`, `support`, `contact`, `marketing`, et leurs variantes
6. Formate les contacts avec Source=`Outlook`
7. Écrit dans l'onglet `ListeContacts_Out` sans doublons

**Filtrage temporel** : le moniteur injecte la variable d'environnement `OUTLOOK_SINCE_DT` avant chaque lancement. L'outil `lire_emails_outlook` ne récupère alors que les messages **postérieurs** à ce timestamp, évitant de retraiter tout l'historique à chaque cycle.

**Premier lancement** : le timestamp est initialisé à "maintenant" — l'historique existant n'est pas traité. Seuls les nouveaux emails à partir du premier lancement sont collectés.

**Outils utilisés** :
- `lire_emails_outlook` — appel Microsoft Graph API
- `ecrire_contacts_sans_doublons` — insertion Google Sheets

---

### Agent 4 — Nettoyeur

**Fichier** : `agents/agent_nettoyeur.py`
**Crew** : `crew_nettoyeur.py`
**Trigger** : présence de tout fichier dans le dossier `ListeContacts_Lin_Out_brute`

**Ce que fait cet agent, en 4 étapes séquentielles :**

**Étape 1 — Suppression des lignes à vérifier**
Lit l'onglet `ListeContacts_Lin_Out_FINAL` et supprime toutes les lignes dont la colonne `A_verifier` vaut `1`. Ces lignes ont été manuellement marquées par l'utilisateur pour exclusion.

**Étape 2 — Application de la liste d'exclusion**
Lit la colonne `Emails exclus` du Google Sheet ListeExclusion et supprime de `ListeContacts_Lin_Out_FINAL` toutes les lignes dont l'email figure dans cette liste.

**Étape 3 — Dédoublonnage**
Supprime les doublons sur la colonne `Email` dans `ListeContacts_Lin_Out_FINAL`. En cas de doublon, la première occurrence (la plus ancienne) est conservée.

**Étape 4 — Archivage**
Tous les fichiers présents dans `ListeContacts_Lin_Out_brute` sont renommés avec la date du jour et déplacés dans Archives. Le dossier source est vidé.

**Outils utilisés** :
- `supprimer_lignes_a_verifier`
- `supprimer_emails_exclus`
- `dedoublonner_google_sheet`
- `archiver_fichier_drive`

---

### Agent 5 — Diffusion_et_Com

**Fichier** : `agents/agent_diffusion_et_com.py`
**Crew** : `crew_diffusion.py`
**Trigger** : présence d'un fichier `ListeContacts_Lin_Out_FINAL` dans le dossier `Diffusion_et_Communication`

**Ce que fait cet agent, en 4 étapes séquentielles :**

**Étape 1 — Lecture des destinataires**
Télécharge le fichier Excel `ListeContacts_Lin_Out_FINAL` depuis le dossier `Diffusion_et_Communication`. Lit la colonne `Email` et filtre les adresses valides (contenant `@`).

**Étape 2 — Lecture du message**
Lit le fichier `ContenuMessage.docx` (ID Drive fixe : `14V2EpnEaO4EW4AHKmNGM6w2An-GWrYhn`). Extrait l'objet (ligne `Objet:`) et le corps du message.

**Étape 3 — Envoi des emails**
Envoie **le même message** à chaque adresse email via l'API Brevo (Sendinblue). Chaque email est envoyé individuellement (pas de champ CC ni BCC groupé). L'expéditeur est défini par les variables `SENDINBLUE_SENDER_EMAIL` et `SENDINBLUE_SENDER_NAME`.

**Étape 4 — Archivage**
Archive `ListeContacts_Lin_Out_FINAL` dans le dossier Archives avec la date dans le nom. `ContenuMessage.docx` reste en place pour être réutilisé lors de campagnes ultérieures.

**Outils utilisés** :
- `lire_emails_depuis_excel_drive`
- `lire_contenu_message_depuis_drive`
- `envoyer_emails_via_sendinblue`
- `archiver_fichier_drive`

---

## 6. Les moniteurs de surveillance

Les moniteurs sont des scripts Python autonomes qui tournent en boucle infinie. Ils constituent le système nerveux automatique du projet : sans eux, les agents ne se déclenchent jamais.

### monitor_main.py — Moniteur principal (agents 1 à 4)

**Lancement** : `python monitor_main.py`
**Fichier d'état** : `.monitor_main_state.json`
**Journal** : `monitor_main.log`

Surveille quatre triggers avec des intervalles distincts :

| Trigger | Condition | Intervalle |
|---|---|---|
| Agent 1 (Connections) | `connections.csv` présent dans `Linkedin_connections` | 15 min |
| Agent 2 (Messages) | `messages.csv` présent dans `Linkedin_messages` | 15 min |
| Agent 3 (Outlook) | Nouveaux emails depuis le dernier cycle | 30 min |
| Agent 4 (Nettoyeur) | Tout fichier présent dans `ListeContacts_Lin_Out_brute` | 15 min |

**Mécanisme anti-boucle infinie** : les IDs des fichiers Drive déjà traités sont persistés dans `.monitor_main_state.json`. Si un agent échoue, le fichier est quand même marqué comme traité pour éviter une tentative infinie.

**Polling Outlook** : le monitor compte le nombre de nouveaux messages depuis le dernier cycle en interrogeant directement l'API Graph (`$filter=receivedDateTime gt {timestamp}`). Si au moins un nouveau message est détecté, il injecte le timestamp dans `OUTLOOK_SINCE_DT` et lance `crew_outlook`. Le timestamp est mis à jour après chaque cycle.

**Structure du fichier d'état `.monitor_main_state.json`** :
```json
{
  "last_check": {
    "connections": 1750000000,
    "messages":    1750000000,
    "outlook":     1750000000,
    "nettoyeur":   1750000000
  },
  "outlook_last_dt": "2026-06-18T10:00:00Z",
  "fichiers_traites": {
    "connections": ["id_fichier_1", "id_fichier_2"],
    "messages":    [],
    "nettoyeur":   []
  }
}
```

---

### monitor_diffusion.py — Moniteur de l'agent 5

**Lancement** : `python monitor_diffusion.py`
**Fichier d'état** : `.monitor_diffusion_state.json`
**Journal** : `monitor_diffusion.log`
**Intervalle** : **20 minutes**

Surveille le dossier `Diffusion_et_Communication`. Détecte tout fichier dont le nom contient `ListeContacts_Lin_Out_FINAL`. Dès qu'un fichier non encore traité est trouvé, lance `crew_diffusion`.

**Mécanisme anti-boucle infinie** : le fichier ID est ajouté à `.monitor_diffusion_state.json` dans un bloc `finally`, même si le crew a échoué.

---

### monitor_exclusion.py — Moniteur ListeExclusion (temps réel)

**Lancement** : `python monitor_exclusion.py`
**Fichier d'état** : `.monitor_state.json`
**Journal** : `monitor_exclusion.log`
**Intervalle** : **10 minutes**

Surveille la colonne `Emails exclus` du Google Sheet ListeExclusion. À chaque cycle :
1. Lit la liste complète des emails exclus
2. Compare avec l'état connu (cycle précédent)
3. Si de nouveaux emails sont apparus, les supprime immédiatement de `ListeContacts_Lin_Out_FINAL` dans le Google Sheet principal
4. Met à jour l'état même si aucune ligne n'a été supprimée (évite les tentatives infinies pour une adresse absente de la liste finale)

Ce moniteur fonctionne **indépendamment** des quatre autres agents. Son seul rôle est la mise à jour en quasi-temps-réel de la liste finale dès qu'une exclusion est décidée.

---

## 7. Mode opératoire — Guide utilisateur

### Prérequis

Avant le premier lancement, s'assurer que :
- Le fichier `.env` est renseigné (voir section 9)
- Le fichier `cles_google.json.json` (compte de service Google) est présent à la racine du projet
- Ollama est installé et le modèle deepseek-r1:8b est téléchargé : `ollama pull deepseek-r1:8b`
- Ollama est en cours d'exécution : `ollama serve` (ou service système actif)
- Le compte de service Google a les droits **Éditeur** sur tous les dossiers Drive et les Google Sheets

### Démarrage en production (mode autonome)

Ouvrir **3 terminaux** et lancer chacun des moniteurs :

```bash
# Terminal 1 — Agents 1 à 4
python monitor_main.py

# Terminal 2 — Agent 5 (diffusion)
python monitor_diffusion.py

# Terminal 3 — Exclusions en temps réel
python monitor_exclusion.py
```

Le système est alors **entièrement autonome**. Les agents se déclenchent seuls dès que leurs conditions sont remplies.

### Procédure : extraire les contacts LinkedIn (Agents 1 & 2)

1. Sur LinkedIn, télécharger l'export des données :
   - Aller dans **Moi → Paramètres → Confidentialité des données → Obtenir une copie de vos données**
   - Sélectionner **Connexions** et/ou **Messages**
   - LinkedIn envoie un email avec un lien de téléchargement (délai de 10 minutes à 24h)
2. Récupérer les fichiers `connections.csv` et/ou `messages.csv`
3. Déposer `connections.csv` dans le dossier Drive **`Linkedin_connections`**
4. Déposer `messages.csv` dans le dossier Drive **`Linkedin_messages`**
5. Dans les 15 minutes, `monitor_main.py` détecte les fichiers et déclenche les agents correspondants
6. Une fois traités, les fichiers sont automatiquement déplacés dans **Archives**

### Procédure : marquer des contacts pour suppression

Pour exclure un contact spécifique **définitivement** de la liste finale :
1. Ouvrir le Google Sheet ListeExclusion
2. Ajouter l'adresse email dans la colonne `Emails exclus` (une adresse par ligne)
3. Dans les 10 minutes, `monitor_exclusion.py` détecte la nouvelle entrée et supprime le contact de `ListeContacts_Lin_Out_FINAL`

Pour marquer un contact comme "à vérifier" (suppression lors du prochain nettoyage) :
1. Ouvrir le Google Sheet principal, onglet `ListeContacts_Lin_Out_FINAL`
2. Mettre la valeur `1` dans la colonne `A_verifier` de la ligne concernée
3. Lors du prochain passage de l'Agent 4, ces lignes seront supprimées

### Procédure : lancer une campagne d'envoi (Agent 5)

1. Préparer le fichier `ContenuMessage.docx` selon le format :
   ```
   Objet: Votre objet d'email

   Corps du message...
   ```
2. S'assurer que `ContenuMessage.docx` est bien dans le dossier Drive **`Diffusion_et_Communication`** (il peut rester d'une campagne précédente, il n'est pas archivé)
3. Déposer dans le dossier Drive **`Diffusion_et_Communication`** le fichier Excel `ListeContacts_Lin_Out_FINAL` contenant les destinataires (colonne `Email` obligatoire)
4. Dans les 20 minutes, `monitor_diffusion.py` détecte le fichier et déclenche l'Agent 5
5. Les emails sont envoyés via Brevo, puis le fichier Excel est archivé automatiquement

### Lancement manuel (sans moniteur)

Pour déclencher un agent sans attendre le polling :

```bash
python crew_connections.py    # Agent 1
python crew_messages.py       # Agent 2
python crew_outlook.py        # Agent 3
python crew_nettoyeur.py      # Agent 4
python crew_diffusion.py      # Agent 5
python main.py                # Agents 1 à 4 en séquence complète
```

### Suivi et journaux

Chaque moniteur produit un fichier de log horodaté :
- `monitor_main.log`
- `monitor_diffusion.log`
- `monitor_exclusion.log`

Format des entrées de log : `jj/mm/aaaa HH:MM:SS [INFO/ERROR] message`

---

## 8. Structure des fichiers du projet

```
Projet_MINER_agents_IA/
│
├── .env                          # Secrets (non versionné)
├── .env.example                  # Modèle de configuration
├── .gitignore                    # Exclusions Git (secrets, venv, états)
├── cles_google.json.json         # Compte de service Google (non versionné)
│
├── llm.py                        # Configuration centralisée du LLM (Ollama)
├── main.py                       # Lancement manuel des agents 1 à 4 en séquence
│
├── crew_connections.py           # Crew agent 1 (run_connections)
├── crew_messages.py              # Crew agent 2 (run_messages)
├── crew_outlook.py               # Crew agent 3 (run_outlook)
├── crew_nettoyeur.py             # Crew agent 4 (run_nettoyeur)
├── crew_diffusion.py             # Crew agent 5 (run_diffusion)
├── crew.py                       # Crew complet agents 1→4 (usage interne)
│
├── monitor_main.py               # Moniteur agents 1 à 4 (polling Drive + Graph API)
├── monitor_diffusion.py          # Moniteur agent 5 (polling dossier Diffusion)
├── monitor_exclusion.py          # Moniteur ListeExclusion (polling Google Sheets)
│
├── agents/
│   ├── agent_extracteur_linkedin.py   # Agent 1 & 2 (LinkedIn)
│   ├── agent_extracteur_outlook.py    # Agent 3 (Outlook)
│   ├── agent_nettoyeur.py             # Agent 4 (Nettoyeur)
│   └── agent_diffusion_et_com.py      # Agent 5 (Diffusion)
│
├── tasks/
│   ├── tasks.py                  # Tâches agents 1 à 4
│   └── task_diffusion.py         # Tâche agent 5
│
├── tools/
│   ├── google_sheets_tools.py    # Lecture, écriture, déduplication, nettoyage Sheets
│   ├── google_drive_tools.py     # Lecture CSV, extraction contacts, archivage Drive
│   ├── outlook_tools.py          # Lecture boîte Outlook via Graph API
│   └── diffusion_tools.py        # Lecture ContenuMessage, Excel, envoi Brevo
│
├── requirements.txt              # Dépendances Python
│
├── .monitor_main_state.json      # État persisté du moniteur principal (non versionné)
├── .monitor_diffusion_state.json # État persisté du moniteur diffusion (non versionné)
├── .monitor_state.json           # État persisté du moniteur exclusion (non versionné)
│
├── monitor_main.log              # Journal du moniteur principal
├── monitor_diffusion.log         # Journal du moniteur diffusion
└── monitor_exclusion.log         # Journal du moniteur exclusion
```

### Rôle des fichiers principaux

**`llm.py`** : point d'entrée unique pour la configuration du LLM. Tous les crews importent `get_llm()` depuis ce fichier. Pour changer de modèle, modifier uniquement ce fichier.

**`tools/google_sheets_tools.py`** : contient les identifiants fixes des Google Sheets (`SHEET_ID` et `SHEET_ID_EXCLUSION`) et la définition des colonnes (`COLONNES_SHEET`). Toute modification du schéma de la feuille doit être répercutée ici.

**`tools/diffusion_tools.py`** : contient `CONTENU_MESSAGE_FILE_ID`, l'ID fixe du fichier `ContenuMessage.docx` dans Drive. Si ce fichier est recréé dans Drive (nouvel ID), cette constante doit être mise à jour.

**`tasks/tasks.py`** : contient tous les IDs de dossiers Drive utilisés par les agents 1 à 4. C'est le fichier de référence pour les dossiers.

---

## 9. Variables d'environnement

Le fichier `.env` doit être créé à la racine du projet en copiant `.env.example` et en renseignant les valeurs réelles.

```env
# LLM local (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
OLLAMA_NUM_CTX=16384

# Google Cloud (compte de service)
GOOGLE_SERVICE_ACCOUNT_FILE=cles_google.json.json

# Microsoft Graph API (boîte Outlook de Pierre Bono)
OUTLOOK_OAUTH_CLIENT_ID=3cc63ea4-8af1-4052-850e-9b77ee3d3c8e
OUTLOOK_OAUTH_TENANT_ID=72ad38fe-0867-4001-ada9-92f6a9fc1025
OUTLOOK_OAUTH_CLIENT_SECRET=<votre_secret>
OUTLOOK_TARGET_MAILBOX=pierre.bono@f-r-d.fr

# Sendinblue / Brevo (agent Diffusion_et_Com)
SENDINBLUE_API_KEY=<votre_cle_api_brevo>
SENDINBLUE_SENDER_EMAIL=<email_expediteur>
SENDINBLUE_SENDER_NAME=<nom_affiche_expediteur>
```

### Description des variables

| Variable | Description |
|---|---|
| `OLLAMA_BASE_URL` | URL de l'instance Ollama (locale par défaut) |
| `OLLAMA_MODEL` | Nom du modèle LLM. Doit être téléchargé via `ollama pull` |
| `OLLAMA_NUM_CTX` | Taille de la fenêtre de contexte (16 384 tokens) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Chemin vers le fichier JSON du compte de service Google |
| `OUTLOOK_OAUTH_CLIENT_ID` | ID de l'application Azure AD |
| `OUTLOOK_OAUTH_TENANT_ID` | ID du tenant Azure AD |
| `OUTLOOK_OAUTH_CLIENT_SECRET` | Secret de l'application Azure AD |
| `OUTLOOK_TARGET_MAILBOX` | Adresse email de la boîte surveillée |
| `SENDINBLUE_API_KEY` | Clé API Brevo (onglet SMTP & API dans l'interface Brevo) |
| `SENDINBLUE_SENDER_EMAIL` | Email de l'expéditeur (doit être vérifié dans Brevo) |
| `SENDINBLUE_SENDER_NAME` | Nom affiché dans le champ "De :" |

### Variable interne injectée par le moniteur

| Variable | Injectée par | Usage |
|---|---|---|
| `OUTLOOK_SINCE_DT` | `monitor_main.py` avant chaque cycle Outlook | Filtre temporel pour Graph API (format ISO 8601 UTC) |

Cette variable n'est **jamais** à renseigner dans `.env`. Elle est gérée automatiquement par le moniteur.

---

## 10. Guide développeur

### Modifier le modèle LLM

Modifier uniquement `llm.py` :
```python
def get_llm() -> ChatOllama:
    return ChatOllama(
        model="llama3:8b",      # ← changer ici
        base_url="http://localhost:11434",
        num_ctx=16384,
    )
```
Tous les crews héritent automatiquement du changement.

### Ajouter une nouvelle source de contacts (Agent 6, etc.)

1. Créer un outil dans `tools/` qui retourne une liste JSON au format `COLONNES_SHEET`
2. Créer un agent dans `agents/` qui utilise cet outil + `ecrire_contacts_sans_doublons`
3. Créer une tâche dans `tasks/tasks.py`
4. Créer un crew `crew_nouvelle_source.py` avec une fonction `run_nouvelle_source()`
5. Ajouter un trigger dans `monitor_main.py` : nouvelle entrée dans `INTERVALS`, nouvelle fonction `check_nouvelle_source(etat)`, l'ajouter dans `CHECKS`

### Modifier les colonnes du Google Sheet

1. Mettre à jour `COLONNES_SHEET` dans `tools/google_sheets_tools.py`
2. Mettre à jour la description des tâches dans `tasks/tasks.py` et `tasks/task_diffusion.py`
3. Mettre à jour les goals et backstories des agents concernés

**Attention** : les colonnes dans Google Sheet doivent être réorganisées manuellement pour correspondre au nouvel ordre.

### Changer les intervalles de polling

Dans `monitor_main.py`, modifier le dictionnaire `INTERVALS` :
```python
INTERVALS = {
    "connections": 15 * 60,   # ← intervalle en secondes
    "messages":    15 * 60,
    "outlook":     30 * 60,
    "nettoyeur":   15 * 60,
}
```

Pour l'agent 5, modifier `POLLING_INTERVAL` dans `monitor_diffusion.py`.
Pour le moniteur d'exclusion, modifier `POLLING_INTERVAL` dans `monitor_exclusion.py`.

### Ajouter des préfixes d'adresses automatiques à exclure (Outlook)

Dans `tools/outlook_tools.py`, ajouter l'entrée dans le set `_AUTO_PREFIXES` :
```python
_AUTO_PREFIXES = {
    ...,
    "nouveau_prefixe",
}
```

### Réinitialiser l'historique Outlook

Supprimer ou vider le fichier `.monitor_main_state.json`. Au prochain démarrage, le timestamp Outlook sera réinitialisé à "maintenant" et l'historique ne sera pas retraité. Pour forcer le retraitement d'une période précise, modifier manuellement `outlook_last_dt` dans ce fichier :
```json
{
  "outlook_last_dt": "2026-01-01T00:00:00Z"
}
```

### Forcer un agent sans attendre le polling

```bash
python crew_connections.py   # ou tout autre crew
```

Le crew peut aussi être importé directement dans un script Python :
```python
from crew_connections import run_connections
rapport = run_connections()
print(rapport)
```

### Ajouter des logs personnalisés

Chaque module utilise le logging standard Python. Pour ajouter des logs dans un outil :
```python
import logging
log = logging.getLogger(__name__)
log.info("Message de diagnostic")
```

Les logs des outils apparaissent dans le terminal du moniteur qui a lancé le crew.

### Architecture des états persistés

Les moniteurs sauvegardent leur état dans des fichiers JSON locaux pour survivre aux redémarrages :

| Fichier | Contenu |
|---|---|
| `.monitor_main_state.json` | Timestamps des derniers cycles, timestamp Outlook, IDs Drive traités |
| `.monitor_diffusion_state.json` | IDs Drive des fichiers déjà diffusés |
| `.monitor_state.json` | Ensemble des emails déjà connus dans ListeExclusion |

Ces fichiers sont dans `.gitignore`. En production, les inclure dans les sauvegardes pour ne pas perdre l'historique de traitement.

---

## 11. Sécurité

### Fichiers secrets — ne jamais commiter

| Fichier | Contenu | Protection |
|---|---|---|
| `.env` | Tous les secrets (clés API, secrets OAuth) | Dans `.gitignore` |
| `cles_google.json.json` | Clé privée du compte de service Google | Dans `.gitignore` |

### Isolation des données

- Le LLM (deepseek-r1:8b via Ollama) tourne **localement**. Aucun nom, email ou contenu de message n'est envoyé à un service d'IA cloud.
- Les données transitent uniquement vers : Google Drive, Google Sheets, Microsoft Graph API (pour la boîte Outlook cible), et Brevo (pour l'envoi des emails).

### Principe de moindre privilège

- Le compte de service Google n'a accès qu'aux dossiers Drive et Sheets explicitement partagés avec lui.
- L'application Azure AD pour Microsoft Graph n'a accès qu'à la boîte Outlook de `pierre.bono@f-r-d.fr`.

### Rotation des secrets

En cas de compromission d'un secret :
1. **Clé Google** : révoquer la clé dans Google Cloud Console → IAM → Comptes de service, générer une nouvelle clé JSON, remplacer `cles_google.json.json`, mettre à jour `GOOGLE_SERVICE_ACCOUNT_FILE` si nécessaire
2. **Secret Azure** : révoquer dans Azure Portal → App registrations → Certificates & secrets, créer un nouveau secret, mettre à jour `OUTLOOK_OAUTH_CLIENT_SECRET` dans `.env`
3. **Clé Brevo** : révoquer dans l'interface Brevo → SMTP & API, créer une nouvelle clé, mettre à jour `SENDINBLUE_API_KEY` dans `.env`
