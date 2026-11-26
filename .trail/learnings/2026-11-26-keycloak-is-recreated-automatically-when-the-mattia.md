---
title: "Keycloak is recreated automatically when the theme changes: deploy.sh labels it with the themes tree hash"
author: Mattia
date: 2026-11-26
branch: main
cost: { minutes: 4, tokens: 157196 }
id: l-056d47d1
scope: repo
status: active
replaces: l-c5173bcf
src: agent
touches:
  - deploy/compose.prod.yaml
  - deploy/deploy.sh
  - deploy/keycloak/themes/argo/login/resources/css/argo.css
  - deploy/keycloak/themes/argo/login/resources/js/argo.js
  - deploy/keycloak/themes/argo/login/theme.properties
---

## Decided
- `deploy/deploy.sh` exports `ARGO_KC_THEME=$(git rev-parse HEAD:deploy/keycloak/themes)`
  and `compose.prod.yaml` puts it in the keycloak `labels`: a theme change alters the label,
  so `up -d` recreates Keycloak (it caches themes and the theme is a bind mount, so a
  plain file change was invisible until a manual restart). ~30-60 s of login downtime
  only on deploys that touch the theme.
- Login theme: `darkMode=false` (dark keycloak.v2 card + dark text from argo.css = black on
  black); the language dropdown is replaced by an IT/EN pill via `login/resources/js/argo.js`
  (`scripts=` in theme.properties) instead of copying keycloak.v2's template.ftl, so
  Keycloak upgrades keep working; without JS the original dropdown stays.

## Watch out
- Running `docker compose up -d` by hand (not via deploy.sh) leaves the label empty and
  recreates Keycloak once.
- The pill relies on `#login-select-toggle` and `kc_locale` in option URLs (Keycloak 26.8):
  check it after a Keycloak upgrade.
