# MINER — Guide de déploiement sur VPS Linux (Ubuntu)

## Prérequis VPS

- OS : Ubuntu 22.04 LTS (utilisateur par défaut : `ubuntu`)
- RAM : minimum 8 Go (16 Go recommandé pour deepseek-r1:8b)
- CPU : 4 vCPU minimum
- Stockage : 20 Go minimum (le modèle LLM pèse ~5 Go)
- Accès SSH avec l'utilisateur `ubuntu`
- Ports sortants ouverts (HTTPS 443) vers Google, Microsoft, Brevo

---

## Étape 1 — Transférer le dossier de production sur le VPS

Depuis votre machine Windows (Git Bash, PowerShell avec OpenSSH, ou WinSCP) :

```bash
# Depuis e:\Projets_Data_et_IA\Projet_MINER_agents_IA\
scp -r MINER_production ubuntu@IP_VPS:/home/ubuntu/Projets_en_Production/MINER
```

Le dossier sera disponible sur le VPS à `/home/ubuntu/Projets_en_Production/MINER/`.

---

## Étape 2 — Copier les fichiers secrets sur le VPS

Ces deux fichiers ne sont jamais dans le dépôt Git. Ils doivent être copiés **manuellement**.

### `cles_google.json.json`

Depuis votre machine Windows :

```bash
scp cles_google.json.json ubuntu@IP_VPS:/home/ubuntu/Projets_en_Production/MINER/
```

### `.env`

Sur le VPS, créer le fichier `.env` à partir du modèle :

```bash
cd /home/ubuntu/Projets_en_Production/MINER
cp .env.example .env
nano .env
```

Remplir toutes les valeurs :

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
OLLAMA_NUM_CTX=16384

GOOGLE_SERVICE_ACCOUNT_FILE=cles_google.json.json

OUTLOOK_OAUTH_CLIENT_ID=<votre_client_id>
OUTLOOK_OAUTH_TENANT_ID=<votre_tenant_id>
OUTLOOK_OAUTH_CLIENT_SECRET=<votre_secret>
OUTLOOK_TARGET_MAILBOX=pierre.bono@f-r-d.fr

SENDINBLUE_API_KEY=<votre_cle_api_brevo>
SENDINBLUE_SENDER_EMAIL=<email_expediteur>
SENDINBLUE_SENDER_NAME=<nom_expediteur>
```

---

## Étape 3 — Lancer le script de déploiement

```bash
cd /home/ubuntu/Projets_en_Production/MINER
bash deploy.sh
```

Le script effectue automatiquement :
1. Installation de Python 3.11, pip, rsync
2. Installation d'Ollama et téléchargement du modèle `deepseek-r1:8b`
3. Installation du virtualenv directement dans `/home/ubuntu/Projets_en_Production/MINER`
4. Création du virtualenv Python et installation des dépendances
5. Installation et activation des 3 services systemd
6. Vérification de la présence des fichiers secrets

---

## Étape 4 — Démarrer les services

```bash
sudo systemctl start miner-main
sudo systemctl start miner-diffusion
sudo systemctl start miner-exclusion
```

Vérifier que tout fonctionne :

```bash
sudo systemctl status miner-main
sudo systemctl status miner-diffusion
sudo systemctl status miner-exclusion
```

---

## Structure finale sur le VPS

```
/home/ubuntu/Projets_en_Production/MINER/               ← répertoire d'installation
├── .env                          ← fichier secret (copié manuellement)
├── .env.example                  ← modèle de référence
├── cles_google.json.json         ← clé compte de service Google (secret)
│
├── agents/                       ← définitions des 5 agents IA
├── tasks/                        ← tâches CrewAI
├── tools/                        ← outils Drive, Sheets, Outlook, Brevo
├── systemd/                      ← fichiers de service (déjà installés dans /etc/systemd/)
│
├── crew_connections.py
├── crew_messages.py
├── crew_outlook.py
├── crew_nettoyeur.py
├── crew_diffusion.py
├── crew.py
│
├── monitor_main.py               ← surveille agents 1 à 4 (15/30 min)
├── monitor_diffusion.py          ← surveille agent 5 (20 min)
├── monitor_exclusion.py          ← surveille ListeExclusion (10 min)
│
├── llm.py
├── main.py
├── requirements.txt
└── .venv/                        ← créé par deploy.sh

/var/log/miner/
├── monitor_main.log
├── monitor_diffusion.log
└── monitor_exclusion.log

/etc/systemd/system/
├── miner-main.service
├── miner-diffusion.service
└── miner-exclusion.service
```

---

## Commandes de gestion courantes

### Voir les logs en temps réel

```bash
# Via journalctl (systemd)
sudo journalctl -u miner-main -f
sudo journalctl -u miner-diffusion -f
sudo journalctl -u miner-exclusion -f

# Via les fichiers de log directement
tail -f /var/log/miner/monitor_main.log
tail -f /var/log/miner/monitor_diffusion.log
tail -f /var/log/miner/monitor_exclusion.log
```

### Arrêter / redémarrer un service

```bash
sudo systemctl stop    miner-main
sudo systemctl restart miner-main
```

### Désactiver le démarrage automatique

```bash
sudo systemctl disable miner-main miner-diffusion miner-exclusion
```

### Lancer un agent manuellement (sans moniteur)

```bash
cd /home/ubuntu/Projets_en_Production/MINER
.venv/bin/python crew_connections.py   # Agent 1
.venv/bin/python crew_messages.py      # Agent 2
.venv/bin/python crew_outlook.py       # Agent 3
.venv/bin/python crew_nettoyeur.py     # Agent 4
.venv/bin/python crew_diffusion.py     # Agent 5
.venv/bin/python main.py               # Agents 1→4 en séquence
```

### Mettre à jour un fichier après modification du code

```bash
# Depuis la machine Windows : transférer le fichier modifié
scp agents/agent_nettoyeur.py ubuntu@IP_VPS:/home/ubuntu/Projets_en_Production/MINER/agents/
# Sur le VPS : redémarrer le service concerné
sudo systemctl restart miner-main
```

---

## Réinitialiser l'historique des moniteurs

```bash
# Réinitialiser Outlook (repart du timestamp "maintenant")
echo '{}' > /home/ubuntu/Projets_en_Production/MINER/.monitor_main_state.json
sudo systemctl restart miner-main

# Réinitialiser le moniteur diffusion (re-traite un fichier déjà archivé)
echo '[]' > /home/ubuntu/Projets_en_Production/MINER/.monitor_diffusion_state.json
sudo systemctl restart miner-diffusion
```

---

## Vérification d'Ollama

```bash
# Tester qu'Ollama répond
curl http://localhost:11434/api/tags

# Vérifier que le modèle est disponible
ollama list

# Re-télécharger si nécessaire
ollama pull deepseek-r1:8b
```

---

## Sécurité

```bash
# Protéger les fichiers secrets
chmod 600 /home/ubuntu/Projets_en_Production/MINER/.env
chmod 600 /home/ubuntu/Projets_en_Production/MINER/cles_google.json.json
```

---

## En cas de problème

| Symptôme | Cause probable | Solution |
|---|---|---|
| Service ne démarre pas | `.env` ou `cles_google.json.json` manquant | Vérifier les fichiers secrets |
| Erreur OAuth Outlook | Secret Azure expiré ou incorrect | Vérifier `OUTLOOK_OAUTH_CLIENT_SECRET` |
| Erreur Google API | Compte de service sans droits | Partager les dossiers Drive avec le compte de service |
| Modèle LLM introuvable | deepseek-r1:8b non téléchargé | `ollama pull deepseek-r1:8b` |
| Ollama ne répond pas | Service Ollama arrêté | `sudo systemctl start ollama` |
| Brevo rejette les emails | Sender email non vérifié | Vérifier l'adresse expéditeur dans l'interface Brevo |
