#!/usr/bin/env bash
# Aggiorna la produzione all'immagine di un commit, senza ricompilare sul server.
#   deploy/deploy.sh <tag>      (tag = SHA del commit, pubblicato da .github/workflows/images.yml)
# Se un servizio non diventa sano entro il tempo limite, termina con errore.
set -euo pipefail
cd "$(dirname "$0")"
TAG=${1:?tag immagine}
export ARGO_IMAGE_TAG=$TAG
ARGO_KC_THEME=$(git rev-parse HEAD:deploy/keycloak/themes)
export ARGO_KC_THEME
dc() { docker compose -f compose.prod.yaml --env-file .env.prod "$@"; }

dc pull --quiet  # tutti i servizi attivi, compreso sync-agent se abilitato
dc up -d --no-build --remove-orphans
for _ in $(seq 1 60); do
  if dc exec -T api python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')" 2>/dev/null; then
    echo "Deploy di $TAG completato: API in salute"
    docker image prune -f >/dev/null
    exit 0
  fi
  sleep 5
done
echo "API non in salute dopo 5 minuti: controlla 'docker compose logs api'" >&2
exit 1
