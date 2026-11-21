# Deploy

Produzione su una VPS Ubuntu Server LTS con Docker Compose (ADR-011). Requisiti indicativi:
2 vCPU, 4 GB RAM, 20 GB disco. Il provider non è ancora scelto (decisione aperta).

## Architettura in produzione

`deploy/compose.prod.yaml`:

| Servizio | Ruolo | Rete |
|---|---|---|
| `caddy` | HTTPS (Let's Encrypt), dashboard statica, proxy verso `api` e `keycloak` | edge (porte 80/443) |
| `api` | FastAPI | edge, backend |
| `worker` | Job di provisioning; raggiunge i SaaS su Internet | edge, backend |
| `migrate` | `alembic upgrade head` a ogni avvio, poi termina | backend |
| `postgres` | `iam_db`; API e worker usano il ruolo `argo_app`, le migrazioni il proprietario | backend (interna) |
| `keycloak` | Identity provider (`start`, dietro proxy) | edge, backend, idp |
| `keycloak-db` | `keycloak_db`, separato (specifica §3.5) | idp (interna) |

Due nomi DNS puntano alla VPS:

- `ARGO_DOMAIN` (es. `argo.azienda.it`): la dashboard e `/api`.
- `ARGO_AUTH_DOMAIN` (es. `accesso.azienda.it`): Keycloak. Le pagine `/admin` sono bloccate
  da Caddy; l'Admin API la usa solo il backend, sulla rete interna.

## Primo deploy

```bash
# sulla VPS
sudo apt install docker.io docker-compose-v2 git
git clone git@github.com:mattiamare9/argo.git && cd argo/deploy
cp .env.prod.example .env.prod        # compila tutti i valori; chmod 600 .env.prod
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443 && ufw enable

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

## Non ancora fatto (Fase 7)

- Monitoraggio e alert esterni (es. uptime check su `/api/health`).
- Rate limiting su `/api/auth/*` e `/api/v1/sync/*`.
- Prova del deploy su una VPS reale: il compose di produzione è validato
  (`docker compose config`) ma non ancora avviato con domini e certificati veri.
