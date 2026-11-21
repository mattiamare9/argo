# Sicurezza

Modello di sicurezza e stato delle misure. Rischi e ragionamento: analisi §7.

## In vigore (Fase 0)

| Misura | Dove |
|---|---|
| Segreti fuori dal repository (`.env` in `.gitignore`, solo `.env.example` versionati) | root |
| PostgreSQL esposto solo su `127.0.0.1` | `deploy/compose.yaml` |
| Container backend con utente non root | `backend/Dockerfile` |
| OpenAPI disattivata in produzione | `app/main.py` |
| Audit log append-only a livello DB (trigger su UPDATE/DELETE/TRUNCATE) | migrazione 0001 |
| Audit scritto nella stessa transazione dell'operazione | `modules/audit/service.py` |
| Lint di sicurezza (Ruff, regole `S` / bandit) | `backend/pyproject.toml` |

## In vigore (Fase 1)

| Misura | Dove |
|---|---|
| Login con passkey (WebAuthn, verifica utente obbligatoria), nessuna password | realm `argo`, flusso `argo browser` |
| Authorization Code Flow + PKCE S256, client confidenziale | `modules/sessions/oidc.py` |
| Sessioni server-side: cookie opaco `HttpOnly; SameSite=Lax` (`Secure` in produzione), in DB solo l'hash | `modules/sessions` |
| Scadenza per inattività 30 min, assoluta 10 h, revoca per utente | `sessions/service.py` |
| `state` legato al browser con cookie dedicato, `nonce` verificato, open redirect bloccato | `sessions/service.py` |
| CSRF: header `X-Argo-CSRF` obbligatorio sulle richieste mutanti, nessun CORS | `sessions/dependencies.py` |
| Ruoli `iam-admin` / `iam-owner`; utenti senza ruolo: 403 | `require_role` |
| Login riusciti, falliti e logout nell'audit | `sessions/service.py` |
| Service account con soli ruoli `manage-users`, `view-users`, `query-users`, `view-realm` | realm |
| Protezione brute force di Keycloak attiva | realm |

## In vigore (Fasi 2–3)

| Misura | Dove |
|---|---|
| Agent autenticati con chiave API (in DB solo SHA-256), connessione solo in uscita | `synchronization` |
| Un dipendente assente dal file non viene mai disattivato | `employees`, `synchronization` |
| Disattivazioni ≥ soglia (default 3) in attesa di conferma, nessuna revoca prima | ADR-020 |
| Snapshot non validi rifiutati per intero e registrati | `synchronization` |
| Ogni tentativo di provisioning nell'audit; i passi riusciti non vengono annullati | `provisioning` |
| Offboarding chiude anche le sessioni della dashboard di Argo | `dashboard.revoke_sessions` |
| Dettagli tecnici degli errori visibili solo all'amministratore | frontend |

## In vigore (Fase 5)

| Misura | Dove |
|---|---|
| Segreti delle applicazioni cifrati (Fernet), chiave solo in variabile d'ambiente, mai restituiti dall'API | `app/core/secrets.py`, `applications` |
| Gestione applicazioni solo `iam-admin` con CSRF; ogni modifica nell'audit senza il segreto | `applications` |
| Credenziali SCIM rifiutate (401/403) = errore definitivo, visibile in dashboard | `connectors/scim.py` |

## In vigore (produzione, `deploy/compose.prod.yaml`)

| Misura | Dove |
|---|---|
| Pubbliche solo 80/443 (Caddy, HTTPS automatico); database su reti interne | compose |
| Console e Admin API di Keycloak non esposte (`/admin` → 404 su Caddy) | `Caddyfile` |
| Header di sicurezza: HSTS, CSP restrittiva, `X-Frame-Options DENY`, `nosniff` | `Caddyfile` |
| Backup cifrati AES-256 (PBKDF2), restore verificato in database separati | `backup.sh`, `restore.sh` |

## Limiti noti

- **Ruoli della dashboard fissati al login** (fino a 10 h): togliere `iam-admin` in Keycloak
  non ha effetto finché la sessione non scade o il dipendente non esce. Correzione prevista:
  revocare le sessioni al cambio di ruolo.

- **Back-channel logout Keycloak → Argo non implementato** (ADR-022): un logout fatto
  direttamente su Keycloak non chiude la sessione della dashboard; la chiude l'offboarding
  o la scadenza per inattività (30 min).
- **Recupero account**: se un utente perde l'unico dispositivo con la passkey, un admin
  rimuove la credenziale dalla console Keycloak e rimanda l'email di registrazione
  (`bootstrap-admin` per gli admin). Nessun recupero self-service, per scelta.
- **Keycloak in sviluppo su HTTP** (`start-dev`); in produzione HTTPS dietro Caddy (Fase 7).
- **Append-only aggirabile dal proprietario della tabella**: oggi l'app si connette con
  l'utente proprietario dello schema, che può disabilitare i trigger. In produzione
  (Fase 7) l'app userà un ruolo DB separato senza privilegi su DDL e trigger.
- `details` dell'audit non viene filtrato automaticamente: chi chiama `audit.record`
  non deve passare segreti.

## Pianificato

- Revoca/rotazione della chiave agent dalla dashboard (oggi solo da DB).
- Primo collegamento: il primo snapshot crea un account e manda un invito passkey a ogni
  dipendente attivo. Decidere se serve una conferma anche per le creazioni di massa.
- Fase 2+: segreti delle integrazioni cifrati in DB, chiave fuori dal DB.
- Fase 7: HTTPS via Caddy, firewall, rate limiting, backup cifrati con restore test.

## Segnalazioni

Segnalare vulnerabilità direttamente al responsabile del progetto, non in issue pubbliche.
