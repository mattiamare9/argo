# ADR-006 – Coda persistente su PostgreSQL

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Nessun RabbitMQ/Redis iniziale; coda su PostgreSQL con `FOR UPDATE SKIP LOCKED`.

## Motivazione

Volumi contenuti, infrastruttura leggera.

## Conseguenze

Worker separato, stessa immagine del backend; retry, backoff, idempotenza.
