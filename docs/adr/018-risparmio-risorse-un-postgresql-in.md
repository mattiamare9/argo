# ADR-018 – Risparmio risorse: un PostgreSQL in sviluppo, Caddy serve il frontend

**Stato:** Accettato
**Origine:** Analisi architetturale 2026-11-21 (docs/ANALISI_ARCHITETTURALE.md)

## Decisione

Sviluppo: una sola istanza PostgreSQL con `iam_db`, `iam_test`, `keycloak_db`. Produzione: container `keycloak-db` separato. Nessun container `frontend`: Caddy serve la build statica.

## Motivazione

PC di sviluppo con risorse limitate; un container in meno in produzione.

## Conseguenze

FastAPI non riceve mai credenziali per `keycloak_db`, nemmeno in sviluppo.
