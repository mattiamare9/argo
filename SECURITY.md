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

## Limiti noti

- **Nessuna autenticazione sulle API**: arriva in Fase 1. Fino ad allora l'API espone
  solo `/api/health` e non va esposta in rete.
- **Append-only aggirabile dal proprietario della tabella**: oggi l'app si connette con
  l'utente proprietario dello schema, che può disabilitare i trigger. In produzione
  (Fase 7) l'app userà un ruolo DB separato senza privilegi su DDL e trigger.
- `details` dell'audit non viene filtrato automaticamente: chi chiama `audit.record`
  non deve passare segreti.

## Pianificato

- Fase 1: login dashboard via Keycloak (BFF, cookie `HttpOnly; Secure; SameSite`, CSRF),
  ruoli `iam-admin` / `iam-owner`, passkey.
- Fase 2: autenticazione dell'agent con chiave API (hash in DB, ruotabile), batch
  idempotenti, conferma admin per disattivazioni di massa (ADR-020).
- Fase 2+: segreti delle integrazioni cifrati in DB, chiave fuori dal DB.
- Fase 7: HTTPS via Caddy, firewall, rate limiting, backup cifrati con restore test.

## Segnalazioni

Segnalare vulnerabilità direttamente al responsabile del progetto, non in issue pubbliche.
