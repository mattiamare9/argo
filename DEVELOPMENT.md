# Sviluppo

Prerequisiti: Docker con Compose, [uv](https://docs.astral.sh/uv/), Node 22+.

Principio: avviare solo ciò che serve. Backend e frontend girano sul host, in container
solo i servizi (PostgreSQL ora, Keycloak dalla Fase 1).

## Prima configurazione

```bash
cp deploy/.env.example deploy/.env      # imposta POSTGRES_PASSWORD
cp backend/.env.example backend/.env    # stessa password negli URL
cd backend && uv sync
cd ../frontend && npm ci
```

I file `.env` sono esclusi da git.

## Avvio

```bash
# PostgreSQL (crea iam_db, iam_test, keycloak_db al primo avvio)
docker compose -f deploy/compose.yaml --profile db up -d --wait

# Backend: http://127.0.0.1:8000/api/docs
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload

# Frontend: http://localhost:5173 (proxy /api → 127.0.0.1:8000)
cd frontend && npm run dev
```

Profili Compose:

| Profilo | Servizi | RAM indicativa |
|---|---|---|
| `db` | postgres | ~40 MB |
| `app` | postgres + api in container | ~100 MB |

Per provare l'immagine del backend: `docker compose -f deploy/compose.yaml --profile app up -d --build`
(le migrazioni vanno applicate prima con `uv run alembic upgrade head` dal host).

## Test e qualità

```bash
cd backend
uv run pytest            # richiede il profilo db attivo; usa il database iam_test
uv run ruff check . && uv run ruff format --check .
uv run alembic check     # modelli e migrazioni allineati

cd frontend
npm run build && npm run lint
```

I test ricreano lo schema di `iam_test` (downgrade + upgrade) a ogni esecuzione e
annullano ogni transazione a fine test.

## Migrazioni

```bash
cd backend
uv run alembic revision --autogenerate --rev-id 0002 -m "descrizione"
```

Rileggere sempre la migrazione generata. Trigger e funzioni SQL si scrivono a mano.

## Nuovo modulo backend

1. `app/modules/<nome>/` con `__init__.py` che esporta l'interfaccia pubblica.
2. Dichiarare le sue dipendenze in `tests/test_module_boundaries.py`.
3. Se ha tabelle, importare `models` in `migrations/env.py`.
4. Test in `tests/<nome>/`.
