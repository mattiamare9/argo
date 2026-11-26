---
title: Keycloak theme changes need a keycloak restart on the VPS; deploy.sh does not do it
author: Mattia
date: 2026-11-26
branch: main
cost: { minutes: 17, tokens: 139200 }
id: l-c5173bcf
scope: repo
status: active
src: agent
touches:
  - deploy/deploy.sh
---

## Decided
- Login theme has `darkMode=false` (`deploy/keycloak/themes/argo/login/theme.properties`):
  keycloak.v2 adds `pf-v5-theme-dark` on `prefers-color-scheme: dark`, the card turns dark
  while `argo.css` keeps dark text, giving black on black. Verified 2026-11-26 with a
  dark-scheme screenshot before/after.
- Email template pins `color-scheme: light only` plus inline colors on body/card.

## Watch out
- The theme is a read-only bind mount from the repo and Keycloak caches themes in
  production: after `git pull`, run `docker compose -f compose.prod.yaml --env-file
  .env.prod restart keycloak`. `deploy/deploy.sh` (`up -d`) does not recreate keycloak for
  file changes, so an automatic deploy alone will not show theme edits.
- Some mobile mail apps (Gmail app) may still force their own dark mode.
