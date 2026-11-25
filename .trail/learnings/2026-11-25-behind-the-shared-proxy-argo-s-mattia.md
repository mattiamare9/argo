---
title: "Behind the shared proxy, Argo's Caddy must rewrite X-Forwarded-For to {client_ip} or rate limiting sees one IP"
author: Mattia
date: 2026-11-25
branch: main
cost: { minutes: 14, tokens: 39550 }
id: l-a68546a4
scope: repo
status: active
src: agent
touches:
  - backend/app/core/ratelimit.py
---

## Decided
The VPS (Aruba, ~10 apps) has one front Caddy in `deploy/proxy/` owning 80/443 and TLS; Argo's
Caddy (`deploy/caddy/Caddyfile`) serves plain `http://` sites on the external Docker network
`proxy` (alias `argo`). Argo's Caddy trusts `private_ranges` and, on `/api/*`, sets
`header_up X-Forwarded-For {client_ip}`.

## Tried and ruled out
Plain `reverse_proxy api:8000` behind two proxies: Caddy appends the front proxy's IP, so
`client_ip()` in `backend/app/core/ratelimit.py` (last XFF entry) gets the front proxy for every
user and the login limit (20/min) becomes global. Without `trusted_proxies`, X-Forwarded-Proto
reaching Keycloak would be `http`.
Path prefixes (`IP/argo`) instead of subdomains: other apps on the same origin could read
Argo's session cookies.

## Watch out
Other apps on the `proxy` network are also "trusted" and could spoof the client IP for the rate
limit. Verified 2026-11-25 with both Caddys chained and stub backends: spoofed XFF dropped,
proto https, /admin 404, HSTS passed through.
