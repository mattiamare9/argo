# Stack tecnologico

Versioni fissate al 2026-11-21. Backend: `backend/pyproject.toml` + `uv.lock`.
Frontend: `frontend/package.json` + `package-lock.json`.

## Backend

| Tecnologia | Versione | Uso |
|---|---|---|
| Python | 3.12 | Linguaggio |
| uv | 0.5.15 | Ambiente, dipendenze, lockfile |
| FastAPI | 0.165.0 | API REST, OpenAPI |
| Uvicorn | 0.54.0 | Server ASGI |
| Pydantic / pydantic-settings | 2.14.4 / 2.16.3 | Validazione, configurazione da env |
| SQLAlchemy (asyncio) | 2.1.9 | ORM |
| asyncpg | 0.32.0 | Driver PostgreSQL async |
| Alembic | 1.20.1 | Migrazioni |
| pytest / pytest-asyncio | 9.2.0 / 1.5.0 | Test |
| httpx | 0.28.1 | Client HTTP (test ora; integrazioni esterne poi) |
| Ruff | 0.17.6 | Lint e formattazione |

## Frontend

| Tecnologia | Versione | Uso |
|---|---|---|
| React | 19.3 | UI |
| TypeScript | 6.0 | Tipi (versione scelta dal template shadcn) |
| Vite | 8 | Build e dev server |
| React Router | 8.5.2 | Routing |
| TanStack Query | 5.108.2 | Richieste API e cache |
| Tailwind CSS | 4 | Stile |
| shadcn/ui (stile base-nova, primitive Base UI) | CLI 4.23.0 | Componenti |
| lucide-react | 1.77 | Icone |
| ESLint, Prettier | 10, 3 | Lint e formattazione |

## Infrastruttura

| Tecnologia | Versione | Uso |
|---|---|---|
| Docker / Compose | 28.5 | Container |
| PostgreSQL | 17.7-alpine | Database |
| python (immagine) | 3.12.12-slim | Base immagine backend |

Pianificati (fasi successive): Keycloak 26.x, Caddy 2.x, Mailpit (solo sviluppo),
step-ca, WireGuard. Le versioni si fissano quando vengono introdotti.
