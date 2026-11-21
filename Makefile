# Comandi ricorrenti. `make ci` esegue in locale le stesse verifiche di .github/workflows/ci.yml.
.PHONY: ci backend agent frontend deploy-config dev-db dev-idp dev-api dev-worker dev-web

ci: backend agent frontend deploy-config

backend:
	cd backend && uv run ruff check . && uv run ruff format --check . \
		&& uv run alembic check && uv run pytest -q

agent:
	cd sync-agent && uv run ruff check . && uv run ruff format --check . && uv run pytest -q

frontend:
	cd frontend && npm run lint && npx prettier --check "src/**/*.{ts,tsx}" && npm run build

deploy-config:
	docker compose -f deploy/compose.yaml --profile idp --profile app config --quiet
	docker run --rm -v "$(CURDIR):/mnt" -w /mnt koalaman/shellcheck:v0.10.0 \
		deploy/backup.sh deploy/restore.sh deploy/deploy.sh deploy/postgres/prod-init.sh

dev-db:
	docker compose -f deploy/compose.yaml --profile db up -d --wait

dev-idp:
	docker compose -f deploy/compose.yaml --profile idp up -d --wait

dev-api:
	cd backend && uv run alembic upgrade head && uv run uvicorn app.main:create_app --factory --reload

dev-worker:
	cd backend && uv run python -m app.worker

dev-web:
	cd frontend && npm run dev
