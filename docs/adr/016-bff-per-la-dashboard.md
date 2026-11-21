# ADR-016 – BFF per la dashboard

**Stato:** Accettato
**Origine:** Analisi architetturale 2026-11-21 (docs/ANALISI_ARCHITETTURALE.md)

## Decisione

Il login OIDC della dashboard lo esegue FastAPI (code flow + PKCE, client confidential). Il browser riceve solo un cookie di sessione `HttpOnly; Secure; SameSite=Lax`.

## Motivazione

Nessun token nel browser; sessioni revocabili lato server (ADR-015, SECURITY §13.2).

## Conseguenze

Serve protezione CSRF sulle richieste mutanti. Implementazione in Fase 1.
