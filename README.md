# Argo IAM

Sistema di Identity and Access Management per una piccola azienda (10–30 dipendenti).
Il titolare aggiorna un file Excel; il sistema rileva le variazioni ATTIVO/INATTIVO e
crea, disabilita o riabilita automaticamente gli accessi.

## Stato

| Fase | Contenuto | Stato |
|---|---|---|
| 0 | Fondamenta: backend, frontend, DB, audit, compose, docs | **Completata** |
| 1 | Keycloak, login dashboard (BFF), passkey | **Completata** |
| 2 | Dipendenti + Sync Agent | **Completata** |
| 3 | Worker, provisioning, offboarding | **Completata** |
| 4–7 | Dispositivi, app/VPN/SaaS, rifinitura, produzione | Da fare |

**Oggi esiste, verificato dal vivo:** il titolare cambia una cella nell'Excel → il Sync Agent
la legge → il backend calcola la transizione → il worker crea, disattiva o riattiva l'account
Keycloak, chiude le sessioni e invia l'invito passkey. Disattivazioni di massa in attesa di
conferma; offboarding parziali visibili e ritentati. Login alla dashboard con passkey.

**Non esiste ancora:** app custom, VPN, SaaS (Fase 5), dispositivi e mTLS (Fase 4),
deploy di produzione (Fase 7). Nessuna funzione è simulata.

## Repository

```text
backend/     FastAPI (api e, da Fase 3, worker)
frontend/    React + TypeScript + Vite (dashboard)
sync-agent/  agent on-premise che legge l'Excel (README dedicato)
e2e/         test end-to-end con passkey virtuale e catture delle pagine
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
