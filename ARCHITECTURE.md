# Architettura

Panoramica sintetica. Il ragionamento completo, i rischi e il piano sono in
[docs/ANALISI_ARCHITETTURALE.md](docs/ANALISI_ARCHITETTURALE.md); le decisioni in [docs/adr/](docs/adr/README.md).

## Componenti

```mermaid
flowchart LR
    subgraph ONPREM[Rete aziendale]
        SRC[Excel o altra fonte] --> AGENT[Sync Agent]
    end
    subgraph VPS
        CADDY[Caddy] --> API[FastAPI]
        CADDY --> STATIC[Build frontend]
        API --> DB[(PostgreSQL iam_db)]
        WORKER[Worker] --> DB
        WORKER --> KC[Keycloak]
        KC --> KCDB[(keycloak_db)]
    end
    AGENT -->|HTTPS in uscita| CADDY
    WORKER --> SAAS[SaaS / VPN / app]
```

## Backend: modular monolith

`backend/app/`:

| Percorso | Contenuto |
|---|---|
| `main.py` | `create_app()`: engine DB, router dei moduli, `/api/health` |
| `core/` | configurazione (`ARGO_*`), logging JSON |
| `db/` | `Base` SQLAlchemy con naming convention, creazione engine |
| `modules/<nome>/` | `models`, `schemas`, `repository`, `service`, `router`, adapter |

Regole (ADR-001, ADR-017):

- Un modulo espone la sua interfaccia pubblica in `__init__.py`. Gli altri moduli
  importano solo `app.modules.<nome>`, mai i file interni.
- Le dipendenze tra moduli sono dichiarate in `backend/tests/test_module_boundaries.py`;
  il test fallisce se un import non è dichiarato.
- I router non contengono logica: chiamano il service. Le query stanno solo nel repository.
- I service non fanno commit quando partecipano a una transazione più ampia
  (es. `audit.record` scrive nella transazione del chiamante).

### Moduli presenti

| Modulo | Stato | Dipende da |
|---|---|---|
| `audit` | Scrittura append-only (`record`). Lettura via API in Fase 1 con l'autenticazione. | – |

Moduli pianificati e grafo delle dipendenze: analisi §4.

## Frontend

`frontend/src/`: `app/` (provider, router), `components/ui` (shadcn/ui),
`components/layout`, `features/<nome>/` (pagine, hook API, tipi della feature), `lib/`.
Ogni feature contiene le proprie chiamate API come hook TanStack Query.

Identità visiva: palette "Linea Argo" (lilla, neutri tinti, solo tema chiaro) definita
come token in `src/index.css`; contesto di prodotto in `frontend/PRODUCT.md`, direzione
della dashboard in `frontend/.impeccable/surfaces/`.

## Dati

- `iam_db`: dati IAM. Schema gestito solo da Alembic (`backend/migrations`).
- `keycloak_db`: interno a Keycloak, mai letto da FastAPI.

| Tabella | Note |
|---|---|
| `audit_events` | Append-only: trigger blocca UPDATE, DELETE, TRUNCATE |
