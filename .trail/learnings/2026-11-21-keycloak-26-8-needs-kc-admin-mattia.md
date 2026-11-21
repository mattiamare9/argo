---
title: "Keycloak 26.8 needs kc-admin-api scope, drops undeclared attributes and rejects IP hosts for WebAuthn"
author: Mattia
date: 2026-11-21
branch: main
cost: { minutes: 3, tokens: 29974 }
id: l-bee523cb
scope: repo
status: active
src: agent
touches:
  - docs/DOMANDE_TITOLARE.md
  - docs/HANDOFF.md
  - deploy/keycloak/argo-realm.json
---

## Decided
- The `argo-backend` service account client has `kc-admin-api` in `defaultClientScopes`
  (`deploy/keycloak/argo-realm.json`). Without it, Keycloak 26.8 issues a valid token with
  `manage-users` roles and the Admin API still answers 401 with no log line.
- Keycloak username = employee_id (ADR-021; `app/modules/identity/keycloak_adapter.py`):
  a custom `employee_id` attribute is silently discarded unless declared in the realm's
  user profile, so lookups by attribute returned 0 users.
- Dev Keycloak is reached as `http://localhost:8080` (`app/core/config.py`): WebAuthn
  refuses an IP address as RP ID, so passkeys never work through 127.0.0.1.
- Email layout lives in `deploy/keycloak/themes/argo/email/html/template.ftl`; message
  bodies go through `kcSanitize`, which strips styling, so they stay plain HTML.

## Tried and ruled out
- Finding users with `?q=employee_id:<id>`: always empty (attribute dropped, see above).
- Debugging the 401 via role mappings and the `sub` claim: both were correct; the cause
  was the missing audience scope.

## Watch out
- The realm JSON is imported only when the realm does not exist: after editing it in dev,
  delete the realm and restart Keycloak (dev users are lost; rerun `bootstrap-admin`).
- Placeholders like `${ARGO_SMTP_HOST}` in the realm must be set on the keycloak container
  in both compose files, or the literal text is imported.
