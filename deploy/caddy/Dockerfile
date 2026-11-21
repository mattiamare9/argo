# Caddy con la build della dashboard inclusa (ADR-018: nessun container frontend separato).
# Contesto di build: la radice del repository.
# Il bundle è statico: si costruisce sull'architettura della macchina di build (veloce
# anche quando l'immagine finale è arm64).
FROM --platform=$BUILDPLATFORM node:22.23.5-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2.11.9-alpine
# Utente non root: il binario ufficiale ha già la capability per le porte 80/443.
RUN addgroup -S caddy && adduser -S -G caddy -H caddy \
    && mkdir -p /data /config && chown -R caddy:caddy /data /config
COPY deploy/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv/frontend
USER caddy
