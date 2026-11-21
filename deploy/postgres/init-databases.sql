-- Eseguito solo alla prima inizializzazione del volume.
-- Sviluppo: un'unica istanza; in produzione Keycloak ha il suo container (ADR-018).
CREATE DATABASE iam_db;
CREATE DATABASE iam_test;
CREATE DATABASE keycloak_db;
