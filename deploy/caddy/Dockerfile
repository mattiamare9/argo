# Caddy con la build della dashboard inclusa (ADR-018: nessun container frontend separato).
# Contesto di build: la radice del repository.
# Il bundle è statico: si costruisce sull'architettura della macchina di build (veloce
# anche quando l'immagine finale è arm64).
FROM --platform=$BUILDPLATFORM node:26.13.1-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2.11.9-alpine
COPY deploy/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv/frontend
