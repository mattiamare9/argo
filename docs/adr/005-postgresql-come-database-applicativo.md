# ADR-005 – PostgreSQL come database applicativo

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Usare PostgreSQL per i dati IAM.

## Motivazione

Transazioni, locking, JSONB, supporto a job persistenti.

## Conseguenze

Database IAM separato da quello di Keycloak (vedi ADR-018 per lo sviluppo).
