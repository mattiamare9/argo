# ADR-020 – Disattivazioni di massa con conferma admin

**Stato:** Accettato
**Origine:** Analisi architetturale 2026-11-21 (docs/ANALISI_ARCHITETTURALE.md)

## Decisione

Le disattivazioni di massa sono ammesse, ma un batch sopra soglia configurabile resta in attesa di conferma di un admin dalla dashboard. Nessuna revoca prima.

## Motivazione

Protegge da errori nel file senza vietare operazioni volontarie.

## Conseguenze

Serve notifica all'admin (email, ADR futuro su SMTP). Implementazione in Fase 2.
