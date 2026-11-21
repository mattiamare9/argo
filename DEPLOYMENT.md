# Deploy

**Non ancora disponibile.** Il deploy di produzione (Caddy, HTTPS, Keycloak con database
dedicato, worker, backup) è pianificato in Fase 7.

Oggi esiste solo l'immagine del backend (`backend/Dockerfile`):

- base `python:3.12.12-slim`, utente non root (`argo`, uid 10001);
- dipendenze installate da `uv.lock` (`--frozen`, senza dipendenze di sviluppo);
- health check su `/api/health`;
- con `ARGO_ENVIRONMENT=production` la documentazione OpenAPI non viene esposta.

Le migrazioni non vengono applicate automaticamente all'avvio del container.
