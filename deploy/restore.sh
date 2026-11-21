#!/usr/bin/env bash
# Ripristina un backup di backup.sh in database NUOVI (non sovrascrive quelli in uso):
#   ./restore.sh <compose-file> <env-file> <backup.tar.gz.enc> <suffisso>
# Esempio di restore test: suffisso "restore_test" → iam_db_restore_test, keycloak_db_restore_test.
set -euo pipefail
COMPOSE_FILE=${1:?compose file}; ENV_FILE=${2:?env file}; BACKUP=${3:?backup}; SUFFIX=${4:?suffisso}
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
: "${ARGO_BACKUP_PASSPHRASE:?imposta ARGO_BACKUP_PASSPHRASE}"
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
dc() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:ARGO_BACKUP_PASSPHRASE -in "$BACKUP" \
  | tar -C "$WORK" -xzf -
for DB in iam_db keycloak_db; do
  TARGET="${DB}_${SUFFIX}"
  dc exec -T postgres createdb -U "$POSTGRES_USER" "$TARGET"
  dc exec -T postgres pg_restore -U "$POSTGRES_USER" --no-owner -d "$TARGET" < "$WORK/$DB.dump"
  echo "Ripristinato $DB in $TARGET"
done
