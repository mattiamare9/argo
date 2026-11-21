#!/bin/sh
# Produzione: ruolo applicativo separato dal proprietario dello schema (SECURITY.md).
# Le migrazioni girano come proprietario; API e worker come argo_app, che non può
# modificare lo schema né disattivare i trigger dell'audit.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE argo_app LOGIN PASSWORD '${ARGO_APP_DB_PASSWORD}';
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO argo_app;
GRANT USAGE ON SCHEMA public TO argo_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argo_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO argo_app;
SQL
