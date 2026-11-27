# Sync Agent in container (sulla VPS, accanto ad Argo): usato quando la fonte è sul web
# (EduPLANWeb). Configurazione montata in /etc/argo-agent/agent.toml, segreti dall'ambiente.
FROM ghcr.io/astral-sh/uv:0.5.15 AS uv

FROM python:3.12.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/venv
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12.12-slim
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# Cartella di stato creata qui: il volume la eredita con il proprietario giusto.
RUN useradd --system --uid 10001 argo && mkdir -p /var/lib/argo-agent \
    && chown argo /var/lib/argo-agent
COPY --from=build /venv /venv
WORKDIR /app
COPY argo_agent ./argo_agent
ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1
USER argo
CMD ["python", "-m", "argo_agent", "--config", "/etc/argo-agent/agent.toml"]
