# ADR-002 – Keycloak come Identity Provider

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Usare Keycloak per autenticazione, OIDC, SAML, WebAuthn e sessioni.

## Motivazione

Non implementare autenticazione proprietaria.

## Conseguenze

FastAPI orchestra il lifecycle tramite Admin REST API; Keycloak autentica.
