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

## Limiti noti

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

- Fase 2: autenticazione dell'agent con chiave API (hash in DB, ruotabile), batch
  idempotenti, conferma admin per disattivazioni di massa (ADR-020).
- Fase 2+: segreti delle integrazioni cifrati in DB, chiave fuori dal DB.
- Fase 7: HTTPS via Caddy, firewall, rate limiting, backup cifrati con restore test.

## Segnalazioni

Segnalare vulnerabilità direttamente al responsabile del progetto, non in issue pubbliche.
