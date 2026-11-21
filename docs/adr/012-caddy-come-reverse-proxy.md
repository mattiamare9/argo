# ADR-012 – Caddy come reverse proxy

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Caddy come unico punto di ingresso HTTP/HTTPS.

## Motivazione

Configurazione semplice, certificati pubblici automatici.

## Conseguenze

Caddy serve anche i file statici del frontend (ADR-018).
