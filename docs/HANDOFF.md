# Handoff – stato del progetto al 2026-11-21

Documento di partenza per la prossima sessione. Leggi questo, poi `README.md`,
`ARCHITECTURE.md` e `docs/DECISIONI_AUTONOME.md`. Le decisioni stabili sono negli ADR
(`docs/adr/`), le regole di interfaccia in `frontend/DESIGN.md` e `frontend/PRODUCT.md`.

## Cos'è Argo, in una frase

IAM per una piccola azienda (10–30 persone): il titolare aggiorna l'elenco dei dipendenti,
un agent on-premise lo legge, il backend calcola chi entra ed esce, un worker crea,
disattiva e riattiva gli account (Keycloak, app via SCIM o passo manuale) e chiude le sessioni.

## Stato

| Area | Stato |
|---|---|
| Fasi 0–3 (fondamenta, login passkey, dipendenti + Sync Agent, provisioning) | Complete, verificate dal vivo |
| Fase 5 (applicazioni) | Registro app + connettori manuale e SCIM 2.0. Mancano VPN e logout delle app custom |
| Fase 7 (produzione) | compose.prod, Caddy HTTPS, ruolo DB `argo_app`, backup/restore verificati, CI/CD, limite richieste, monitoraggio. **Mai avviata su una VPS reale** |
| Fase 4 (dispositivi, mTLS) | Rimandata: proposta di non farla nel primo rilascio |
| Dashboard | Panoramica (linea dei servizi + quadro chiavi), Dipendenti, Sincronizzazione (con chiavi agent), Operazioni, Applicazioni, Registro |
| Email | Tema Argo; Microsoft 365 via OAuth2 configurabile, non ancora collegato |

Test: backend ~125 (pytest su PostgreSQL), sync-agent 24, E2E passkey con autenticatore
virtuale (`e2e/`). CI e immagini multi-arch (amd64 + arm64) verdi su GitHub.

## Come riprendere

```bash
make dev-db            # o: make dev-idp per Keycloak + Mailpit (~500 MB)
make dev-api           # migrazioni + API su :8000
make dev-worker        # job di provisioning
make dev-web           # dashboard su http://localhost:5173 (sempre localhost, mai 127.0.0.1)
make ci                # stesse verifiche della CI
```

Primo accesso in sviluppo: `cd backend && uv run python -m app.cli bootstrap-admin ...`,
poi il link in Mailpit (http://127.0.0.1:8025). Test E2E: `cd e2e && npm run passkey`.

## Prossimi passi, in ordine

1. **Risposte del titolare** (`docs/DOMANDE_TITOLARE.md`): sbloccano la produzione.
2. **Fonte dipendenti dal sito web**: nuovo `SourceReader` in `sync-agent/argo_agent/sources/`
   (contratto invariato: `docs/sync-api.md`). Il resto non cambia.
3. **Prima installazione sulla VPS Aruba** (195.231.64.149, 8 vCPU / 16 GB, condivisa con
   altre app dietro `deploy/proxy`): seguire `DEPLOYMENT.md`,
   poi attivare il deploy automatico (`DEPLOY_ENABLED` + segreti SSH).
4. **Email Microsoft 365**: app Entra ID con `SMTP.SendAsApp` (`DEPLOYMENT.md`, sezione Email).
5. Dopo: conservazione dei log, connettori per i programmi reali, eventuale VPN.

## Cose che non sono ovvie (lette sul campo)

- Keycloak 26.8: l'Admin API vuole lo scope `kc-admin-api` sul service account (senza: 401).
- Keycloak 26: attributi utente non dichiarati vengono scartati → username = employee_id (ADR-021).
- WebAuthn non accetta IP come dominio: Keycloak va raggiunto via `localhost` in sviluppo.
- Il realm si importa solo se non esiste: dopo modifiche a `argo-realm.json` in sviluppo,
  elimina il realm e riavvia Keycloak (gli utenti di sviluppo si perdono: rifai bootstrap).
- In produzione issuer pubblico ≠ URL interno di Keycloak (`ARGO_KEYCLOAK_PUBLIC_URL`).
- Un passo "account non trovato" non è un successo: diventa manuale (revisione di sicurezza).
- Ogni passo del worker ricontrolla lo stato attuale del dipendente: un retry vecchio non
  annulla un cambio più recente.
- Le email passano da `kcSanitize`: lo stile va in `template.ftl`, non nei messaggi.
- Learnings della sessione: `.trail/learnings/` (trail è inizializzato).

## Servizi lasciati accesi sulla macchina di sviluppo

API (:8000), worker, Vite (:5173), container `argo-postgres-1`, `argo-keycloak-1`,
`argo-mailpit-1`. Per fermare: `docker compose -f deploy/compose.yaml --profile idp down`
e chiudere i processi. Dati di prova nel DB di sviluppo: dipendenti 1001–1006, app manuale
"FatturaFacile", un passo manuale aperto e uno fallito (impostato a mano per le catture).
