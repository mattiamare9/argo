# Deploy

Guida passo passo per la VPS Aruba: `docs/GUIDA_VPS.md`.

Produzione su una VPS Ubuntu Server LTS con Docker Compose (ADR-011). Requisiti indicativi:
2 vCPU, 4 GB RAM, 20 GB disco per Argo. VPS scelta: Aruba, 8 vCPU, 16 GB RAM, 160 GB,
condivisa con altre app (circa una decina).

## Architettura in produzione

Sulla VPS c'è un **proxy principale** (`deploy/proxy/`): l'unico container con le porte
80/443, fa i certificati HTTPS per tutte le app e smista per nome di dominio. Ogni app ha
il suo compose e si collega alla rete Docker `proxy` senza pubblicare porte. Per una nuova
app: record DNS verso la VPS, un file `deploy/proxy/sites/<app>.caddy` (fuori dal
repository), `docker compose restart caddy` in `deploy/proxy`.

```
Internet :80/:443 → proxy (HTTPS) ─┬─ argo.azienda.it, accesso.azienda.it → caddy di Argo
                                   └─ altre app, un sottodominio ciascuna
```

Ogni app sul suo sottodominio, non sotto un percorso (`/argo`): sullo stesso dominio le
altre app potrebbero leggere i cookie di sessione di Argo.

`deploy/compose.prod.yaml`:

| Servizio | Ruolo | Rete |
|---|---|---|
| `caddy` | Dietro il proxy principale (solo HTTP): header di sicurezza, dashboard statica, proxy verso `api` e `keycloak`, blocco di `/admin` | edge, proxy (alias `argo`) |
| `api` | FastAPI | edge, backend |
| `worker` | Job di provisioning; raggiunge i SaaS su Internet | edge, backend |
| `migrate` | `alembic upgrade head` a ogni avvio, poi termina | backend |
| `postgres` | `iam_db`; API e worker usano il ruolo `argo_app`, le migrazioni il proprietario | backend (interna) |
| `keycloak` | Identity provider (`start`, dietro proxy) | edge, backend, idp |
| `keycloak-db` | `keycloak_db`, separato (specifica §3.5) | idp (interna) |
| `sync-agent` | Solo con `COMPOSE_PROFILES=eduplan`: legge i dipendenti da EduPLANWeb ogni 15 minuti e li invia all'API interna | edge |

Due nomi DNS puntano alla VPS:

- `ARGO_DOMAIN` (es. `argo.azienda.it`): la dashboard e `/api`.
- `ARGO_AUTH_DOMAIN` (es. `accesso.azienda.it`): Keycloak. Le pagine `/admin` sono bloccate
  da Caddy; l'Admin API la usa solo il backend, sulla rete interna.

## CI/CD (GitHub Actions)

| Workflow | Quando | Cosa fa |
|---|---|---|
| `ci.yml` | ogni push e PR | backend (lint, migrazioni: una sola head, upgrade, `alembic check`, downgrade/upgrade, test su PostgreSQL), sync-agent, frontend (lint, prettier, build), compose e script (`shellcheck`), sicurezza (gitleaks, pip-audit, npm audit, Trivy config) |
| `images.yml` | push su `main`, tag `v*` | immagini `argo-backend`, `argo-caddy` e `argo-sync-agent` per **amd64 e arm64** (Oracle Ampere) su GHCR, tag = SHA del commit + `main` + versione; scansione Trivy delle immagini; poi deploy |
| Dependabot | ogni lunedì | una PR raggruppata per Python, npm, Actions, Docker |

`make ci` esegue in locale le stesse verifiche di `ci.yml`.

**Deploy automatico** (spento finché la VPS non esiste): dopo il build, il job `deploy`
entra in SSH sul server e lancia `deploy/deploy.sh <sha>`, che scarica le immagini del
commit (nessuna build sul server), riavvia i servizi e aspetta che l'API sia in salute.
Per attivarlo, in GitHub → Settings → Secrets and variables → Actions:

- variabile `DEPLOY_ENABLED=true`;
- segreti `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (chiave dedicata, solo deploy),
  `DEPLOY_KNOWN_HOSTS` (output di `ssh-keyscan <host>`);
- environment `production` (facoltativo: approvazione manuale prima di ogni deploy).

Rollback: `deploy/deploy.sh <sha-precedente>` sul server, o rilanciare il workflow di un
commit precedente. Le migrazioni non si annullano da sole: un rollback oltre una
migrazione richiede `alembic downgrade` esplicito.

**Cambio provider**: tutto è in immagini multi-arch su GHCR e in `deploy/`; su un'altra VPS
bastano Docker, il clone del repository, `.env.prod` e il restore dell'ultimo backup.

## Primo deploy

```bash
# sulla VPS
sudo apt install docker.io docker-compose-v2 git
git clone git@github.com:mattiamare9/argo.git && cd argo/deploy
cp .env.prod.example .env.prod        # compila tutti i valori; chmod 600 .env.prod
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443 && ufw enable
# Aruba: apri 22/80/443 anche nel firewall del pannello.

# proxy principale, una volta per tutta la VPS (crea la rete `proxy`)
(cd proxy && cp .env.example .env && docker compose up -d)   # compila prima .env

docker compose -f compose.prod.yaml --env-file .env.prod up -d --build
docker compose -f compose.prod.yaml --env-file .env.prod ps    # tutti healthy / running

# primo amministratore (riceve l'email per registrare la passkey)
docker compose -f compose.prod.yaml --env-file .env.prod exec api \
  python -m app.cli bootstrap-admin --employee-id ADMIN --email it@azienda.it \
  --first-name Nome --last-name Cognome

# chiave per il Sync Agent (mostrata una sola volta)
docker compose -f compose.prod.yaml --env-file .env.prod exec api \
  python -m app.cli create-agent --name excel-hr
```

Poi installa il Sync Agent sul server aziendale (`sync-agent/README.md`) con
`api_url = "https://<ARGO_DOMAIN>"`.

## Email (inviti passkey)

Mailpit serve solo in sviluppo: cattura le email e le mostra in una pagina, non le spedisce.
In produzione Keycloak invia tramite un vero server SMTP.

**Microsoft 365** (l'azienda usa Microsoft): Microsoft ha ritirato l'accesso SMTP con sola
password, quindi si usa OAuth2. Keycloak 26.8.2 lo supporta (verificato nell'interfaccia di
amministrazione: `authType` "token"). Passi, da fare con l'amministratore Microsoft:

1. In Entra ID registra un'app (es. "Argo mail"), crea un client secret, concedi il
   permesso applicativo `SMTP.SendAsApp` di Office 365 Exchange Online con consenso admin.
2. In Exchange Online registra il service principal dell'app e dagli il permesso di
   inviare come la casella mittente (es. `argo@azienda.it`). Richiede PowerShell
   Exchange: da verificare insieme, i comandi esatti dipendono dal tenant.
3. In `.env.prod`:

```
ARGO_SMTP_HOST=smtp.office365.com
ARGO_SMTP_PORT=587
ARGO_SMTP_STARTTLS=true
ARGO_SMTP_AUTH=true
ARGO_SMTP_USER=argo@azienda.it
ARGO_SMTP_FROM=argo@azienda.it
ARGO_SMTP_AUTH_TYPE=token
ARGO_SMTP_TOKEN_URL=https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
ARGO_SMTP_TOKEN_SCOPE=https://outlook.office365.com/.default
ARGO_SMTP_TOKEN_CLIENT_ID=<application-id>
ARGO_SMTP_TOKEN_CLIENT_SECRET=<client-secret>
```

Alternativa senza Microsoft: un servizio SMTP dedicato (utente/password, `ARGO_SMTP_AUTH_TYPE=basic`).

## Aggiornamento

```bash
git pull
docker compose -f compose.prod.yaml --env-file .env.prod up -d --build
```

Le migrazioni partono da sole (`migrate`); `api` e `worker` ripartono dopo.

Il realm Keycloak si importa **solo al primo avvio**: le modifiche successive a
`deploy/keycloak/argo-realm.json` vanno applicate dalla console Keycloak o con l'Admin API.

## Backup e restore

```bash
# backup cifrato di iam_db + keycloak_db + realm (pianificalo con cron, es. ogni notte)
./backup.sh compose.prod.yaml .env.prod /var/backups/argo
# copia il file FUORI dalla VPS (es. rclone verso uno storage esterno)

# restore test periodico: ripristina in database nuovi e confronta
./restore.sh compose.prod.yaml .env.prod /var/backups/argo/argo-<data>.tar.gz.enc restore_test
```

- Cifratura AES-256 (openssl, PBKDF2 600k iterazioni). La passphrase
  `ARGO_BACKUP_PASSPHRASE` va conservata fuori dalla VPS: senza, il backup è illeggibile.
- `restore.sh` non tocca i database in uso: crea `iam_db_<suffisso>` e
  `keycloak_db_<suffisso>`. Per un ripristino reale si fermano i servizi e si rinominano.
- Verificato in sviluppo il 2026-11-21: conteggi di dipendenti, audit e utenti Keycloak
  identici dopo il ripristino, trigger append-only presenti, passphrase errata rifiutata.

## Monitoraggio

- Configurare un servizio di uptime esterno (anche gratuito) su
  `https://<ARGO_DOMAIN>/api/health`, con controllo ogni 5 minuti e avviso via email.
- Risponde 503 sia se il database non è raggiungibile sia se il worker non dà segni di vita
  da più di 2 minuti (`"worker": "stale"`). Senza worker mai avviato risponde 200 con
  `"worker": "unknown"`.
- `docker compose ps` mostra lo stato degli healthcheck dei container.

## Non ancora fatto (Fase 7)

- Prova del deploy su una VPS reale: il compose di produzione è validato
  (`docker compose config`) ma non ancora avviato con domini e certificati veri.
