# Argo IAM

Sistema di Identity and Access Management per una piccola azienda (10–30 dipendenti).
Il titolare aggiorna un file Excel; il sistema rileva le variazioni ATTIVO/INATTIVO e
crea, disabilita o riabilita automaticamente gli accessi.

## Stato

| Fase | Contenuto | Stato |
|---|---|---|
| 0 | Fondamenta: backend, frontend, DB, audit, compose, docs | **Completata** |
| 1 | Keycloak, login dashboard (BFF), passkey | Da fare |
| 2 | Dipendenti + Sync Agent | Da fare |
| 3 | Worker, provisioning, offboarding | Da fare |
| 4–7 | Dispositivi, app/VPN/SaaS, rifinitura, produzione | Da fare |

**Oggi esiste:** API FastAPI con `/api/health`, audit log append-only, migrazioni Alembic,
shell della dashboard che mostra lo stato del sistema.
**Non esiste ancora:** autenticazione, sincronizzazione, provisioning. Nessuna funzione
è simulata.

## Repository

```text
backend/     FastAPI (api e, da Fase 3, worker)
frontend/    React + TypeScript + Vite (dashboard)
sync-agent/  agent on-premise (da Fase 2)
deploy/      Docker Compose, configurazioni
docs/        analisi architetturale e ADR
```

## Documentazione

- [ARCHITECTURE.md](ARCHITECTURE.md): architettura e moduli
- [TECH_STACK.md](TECH_STACK.md): tecnologie e versioni
- [DEVELOPMENT.md](DEVELOPMENT.md): ambiente di sviluppo, test
- [DEPLOYMENT.md](DEPLOYMENT.md): deploy (non ancora disponibile)
- [SECURITY.md](SECURITY.md): modello di sicurezza
- [docs/adr/](docs/adr/README.md): decisioni architetturali
- [docs/ANALISI_ARCHITETTURALE.md](docs/ANALISI_ARCHITETTURALE.md): analisi iniziale e piano
