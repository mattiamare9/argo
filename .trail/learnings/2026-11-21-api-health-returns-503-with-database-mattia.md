---
title: "/api/health returns 503 with database ok when the worker is stale"
author: Mattia
date: 2026-11-21
branch: main
cost: { minutes: 4, tokens: 12345 }
id: l-590a59ed
scope: repo
status: active
src: agent
touches:
  - DEPLOYMENT.md
  - SECURITY.md
  - backend/app/core/config.py
  - backend/app/core/ratelimit.py
  - backend/app/main.py
  - backend/app/modules/jobs/__init__.py
  - backend/app/modules/jobs/models.py
  - backend/app/modules/jobs/service.py
  - backend/app/modules/sessions/router.py
  - backend/app/modules/synchronization/router.py
---

## Decided
- `/api/health` (`backend/app/main.py`) answers 503 for an unreachable database OR a stale
  worker heartbeat (`jobs.worker_status`, older than 2 minutes), so one external uptime
  check covers both. "unknown" (no heartbeat rows, e.g. dev without a worker) stays 200.
- The dashboard reads the `worker` field explicitly (`frontend/src/features/dashboard/status.ts`,
  `workerStale`): a 503 alone is not "API down", because `fetchHealth` accepts 503 bodies.

## Watch out
- Any new consumer of `/api/health` must look at `worker`, not only `database`: a stale
  worker returns `{"status":"degraded","database":"ok","worker":"stale"}`, and checking
  `database` alone reports everything fine while joiners and leavers sit in the queue.
- The worker healthcheck in `deploy/compose.prod.yaml` is disabled; worker liveness is
  only visible through this endpoint.
