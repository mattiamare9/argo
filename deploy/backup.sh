#!/usr/bin/env bash
# Backup cifrato dei due database (iam_db e keycloak_db). Uso, da deploy/:
#   ./backup.sh <compose-file> <env-file> <cartella-destinazione>
# Il file prodotto va copiato FUORI dalla VPS (specifica §13.4).
set -euo pipefail
COMPOSE_FILE=${1:?compose file}; ENV_FILE=${2:?env file}; DEST=${3:?cartella}
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
: "${ARGO_BACKUP_PASSPHRASE:?imposta ARGO_BACKUP_PASSPHRASE}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$DEST/argo-$STAMP.tar.gz.enc"
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
dc() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

if dc ps --services | grep -qx keycloak-db; then        # produzione: due istanze
  dc exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc iam_db > "$WORK/iam_db.dump"
  dc exec -T keycloak-db pg_dump -U keycloak -Fc keycloak_db > "$WORK/keycloak_db.dump"
else                                                     # sviluppo: istanza unica
  dc exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc iam_db > "$WORK/iam_db.dump"
  dc exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc keycloak_db > "$WORK/keycloak_db.dump"
fi
cp keycloak/argo-realm.json "$WORK/"
tar -C "$WORK" -czf - . | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt \
  -pass env:ARGO_BACKUP_PASSPHRASE -out "$OUT"
echo "Backup scritto: $OUT ($(du -h "$OUT" | cut -f1))"
