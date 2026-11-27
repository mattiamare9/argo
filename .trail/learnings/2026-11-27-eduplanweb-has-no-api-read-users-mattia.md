---
title: "EduPLANWeb has no API: read users from the JSON endpoint behind its Users table, keyed by Id"
author: Mattia
date: 2026-11-27
branch: main
cost: { minutes: 19, tokens: 264708 }
id: l-9306b17f
scope: repo
status: active
src: agent
touches:
  - sync-agent/argo_agent/sources/eduplan.py
  - sync-agent/tests/test_eduplan.py
---

## Decided
- Source = `POST /Configurazione/ReadUsers?tenantId=1` with `includiDisattivi=true`, after the
  ASP.NET login form (`__RequestVerificationToken`). It is what fills the Users table; the
  "Export excel" button builds the xlsx in the browser from the same data, no request.
  Plain httpx, no browser (`sync-agent/argo_agent/sources/eduplan.py`).
- `employee_id` = EduPLANWeb `Id` (stable int); status = `Attivo`.
- Unusable accounts are skipped and logged instead of failing the whole snapshot (the backend
  never deactivates someone missing from a snapshot, so skipping is safe). Same email on
  several accounts: keep the only active one (re-created account), else none.
- Runs on the VPS as `sync-agent` (profile `eduplan`, `COMPOSE_PROFILES` read from .env.prod),
  every 15 min, not only at midnight: the dashboard flags the agent as silent after 2 h.

## Tried and ruled out
- The exported Excel: only active accounts, no stable id (username glued to full name).
- Playwright: unnecessary, the login is a plain form post.

## Watch out
- Failed login returns 200 on `/Account/Login`; unauthenticated `ReadUsers` returns 404.
- Real data 2026-11-27: 56 accounts, 35 usable, 21 skipped (12 without surname, mostly
  "DA ASSEGNARE" placeholders; 9 in shared-email groups). Not an official API: may break.
