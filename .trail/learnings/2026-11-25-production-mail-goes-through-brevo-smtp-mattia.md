---
title: "Production mail goes through Brevo SMTP (already authenticated on safetia.it), not Microsoft 365 OAuth2"
author: Mattia
date: 2026-11-25
branch: main
cost: { minutes: 34, tokens: 47905 }
id: l-dc367346
scope: repo
status: active
src: agent
touches:
  - docs/GUIDA_VPS.md
  - DEPLOYMENT.md
  - ".github/workflows/ci.yml"
  - deploy/.env.prod.example
  - deploy/caddy/Caddyfile
  - deploy/compose.prod.yaml
  - deploy/proxy/.env.example
  - deploy/proxy/Caddyfile
  - deploy/proxy/compose.yaml
  - deploy/proxy/sites/.gitkeep
---

## Decided
- Invites are sent through Brevo SMTP relay (`smtp-relay.brevo.com:587`, STARTTLS,
  `ARGO_SMTP_AUTH_TYPE=basic`, dedicated SMTP key). Public DNS of safetia.it already has
  Brevo DKIM (`brevo1/brevo2._domainkey`) and DMARC, so no Microsoft 365 admin is needed;
  the M365 OAuth2 path in `DEPLOYMENT.md` stays as the alternative.
- Domains: `accessi.safetia.it` = ARGO_DOMAIN (already points to 195.231.64.149),
  `login.safetia.it` proposed for ARGO_AUTH_DOMAIN (Keycloak).
- On the VPS everything runs as root with key-only SSH, repo cloned over HTTPS in
  `/root/argo` (the deploy job in `.github/workflows/images.yml` does `cd argo`). A
  separate user in the `docker` group would be root-equivalent; ufw skipped because the
  Aruba panel firewall allows only 22/80/443 and Docker bypasses ufw for published ports.

## Watch out
- Brevo link tracking may rewrite the one-time activation link: check it is off for
  transactional mail on the first test invite (not yet verified).
- Keycloak stores domain and SMTP from `.env.prod` at the first realm import: start Argo
  only with the real values.
- The GitHub deploy key is a root key on the server.
