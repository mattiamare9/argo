# ADR-014 – Adapter per le integrazioni esterne

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Ogni integrazione esterna passa da una porta (interfaccia) e un adapter.

## Motivazione

Evitare dipendenze dirette tra logica e API dei fornitori.

## Conseguenze

Keycloak, VPN, SaaS sostituibili con modifiche circoscritte. Collocazione: ADR-017.
