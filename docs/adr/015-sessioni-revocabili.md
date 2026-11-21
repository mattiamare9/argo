# ADR-015 – Sessioni revocabili

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Le applicazioni custom usano sessioni server-side revocabili.

## Motivazione

Disabilitare un account non invalida i JWT già emessi.

## Conseguenze

Token brevi, back-channel logout, offboarding `PARTIAL` finché le app non confermano.
