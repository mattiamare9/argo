# Stessa immagine per api e worker (deploy/compose.yaml: il worker usa `python -m app.worker`).
FROM ghcr.io/astral-sh/uv:0.5.15 AS uv

FROM python:3.12.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/venv
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12.12-slim
RUN useradd --system --uid 10001 argo
COPY --from=build /venv /venv
WORKDIR /app
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1
USER argo
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
