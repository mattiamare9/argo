# ADR-012 – Caddy come reverse proxy

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Caddy come unico punto di ingresso HTTP/HTTPS.

## Motivazione

Configurazione semplice, certificati pubblici automatici.

## Conseguenze

Caddy serve anche i file statici del frontend (ADR-018).

Aggiornamento 2026-11-25: la VPS ospita anche altre app. L'HTTPS passa a un proxy
principale condiviso (`deploy/proxy`, sempre Caddy); il Caddy di Argo resta dietro di
esso, in HTTP sulla rete `proxy`, con header di sicurezza, dashboard e blocco di `/admin`.
