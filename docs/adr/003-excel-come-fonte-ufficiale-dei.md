# ADR-003 – Excel come fonte ufficiale dei dipendenti

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Il file Excel condiviso è la fonte ufficiale dello stato dei dipendenti.

## Motivazione

Il gestionale non espone API per il lifecycle degli utenti.

## Conseguenze

Serve un Sync Agent con validazione rigorosa. Vedi ADR-019: la fonte è sostituibile.
