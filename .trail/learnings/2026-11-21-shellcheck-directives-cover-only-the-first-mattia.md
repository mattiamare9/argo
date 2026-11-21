---
title: shellcheck directives cover only the first command of a ;-joined line
author: Mattia
date: 2026-11-21
branch: main
cost: { minutes: 93, tokens: 1391982 }
id: l-7df65eec
scope: repo
status: active
src: agent
touches:
  - docs/DECISIONI_AUTONOME.md
  - ".github/workflows/images.yml"
  - DEPLOYMENT.md
  - backend/Dockerfile
  - deploy/.env.prod.example
  - deploy/caddy/Dockerfile
  - deploy/compose.prod.yaml
  - deploy/compose.yaml
  - deploy/keycloak/argo-realm.json
  - ".github/dependabot.yml"
---

## Decided
- In `deploy/backup.sh` and `deploy/restore.sh` the env file is loaded on three separate
  lines (`set -a`, `# shellcheck source=/dev/null`, `. "$ENV_FILE"`, `set +a`), so the
  directive sits directly above the `source` command. CI runs shellcheck on these scripts
  (`.github/workflows/ci.yml`, job `deploy-config`) and fails on warnings.

## Tried and ruled out
- `# shellcheck disable=SC1090` above `set -a; . "$ENV_FILE"; set +a`: the directive
  applied only to `set -a`, and SC1090 was still reported on the `.` command.
- Moving the same directive without splitting the line: same result.

## Watch out
- Shellcheck is not installed on the dev machine; `make deploy-config` runs it via the
  pinned `koalaman/shellcheck:v0.10.0` image, the same check CI does.
