# Argo Sync Agent

Servizio on-premise che legge in sola lettura il file Excel dei dipendenti, lo valida e invia
al backend Argo (via HTTPS) l'elenco **completo** dei dipendenti. Contratto API:
`docs/sync-api.md`.

**Regola di sicurezza:** un dipendente assente dal file non viene mai disattivato. Solo un
passaggio esplicito a `INATTIVO` produce un offboarding. Se il file è mancante, vuoto, corrotto
o non valido, l'agent non invia nulla e segnala lo stato "sospeso" al backend.

L'agent invia uno snapshot quando il contenuto cambia e comunque ogni `heartbeat_seconds`
(default 1 ora). Il file viene copiato in un file temporaneo prima della lettura (nessun lock
sull'originale) e letto solo dopo che dimensione e data di modifica sono stabili per
`stable_seconds`. I file di lock di Office (`~$...`) sono ignorati.

## Installazione

Richiede Python 3.12 e [uv](https://docs.astral.sh/uv/).

```bash
cd sync-agent
uv sync
cp agent.example.toml agent.toml   # poi modificare
```

## Configurazione

File TOML (`--config`, default `agent.toml`); vedere `agent.example.toml`. La chiave API **non**
va nel file: si passa solo con la variabile d'ambiente `ARGO_AGENT_API_KEY`.

```bash
export ARGO_AGENT_API_KEY='...'
uv run python -m argo_agent --config agent.toml          # ciclo continuo
uv run python -m argo_agent --config agent.toml --once   # un solo ciclo (cron, prove)
```

Lo stato locale (hash dell'ultimo invio accettato) è in `state_dir/state.json`. Se manca o è
corrotto l'agent reinvia tutto: è innocuo, il backend è idempotente.

## Servizio systemd (Linux)

`/etc/systemd/system/argo-sync-agent.service`:

```ini
[Unit]
Description=Argo Sync Agent
After=network-online.target
Wants=network-online.target

[Service]
User=argo-agent
WorkingDirectory=/opt/argo/sync-agent
EnvironmentFile=/etc/argo-agent.env
ExecStart=/usr/local/bin/uv run python -m argo_agent --config /etc/argo-agent.toml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

`/etc/argo-agent.env` (permessi 600) contiene `ARGO_AGENT_API_KEY=...`. Poi:
`systemctl enable --now argo-sync-agent`.

Un wrapper come servizio Windows è una decisione rimandata.

## Struttura del file Excel

- Prima riga: intestazioni; dalla seconda riga un dipendente per riga (righe vuote ignorate).
- Colonne obbligatorie (i nomi si possono cambiare in `[columns]`): `employee_id`, `email`,
  `first_name`, `last_name`, `status`.
- `status`: `ATTIVO` o `INATTIVO` (modificabili in `[status_values]`, senza distinzione tra
  maiuscole e minuscole).
- Foglio: il primo, oppure quello indicato da `sheet`.
- Regole: nessun campo vuoto, `employee_id` ed `email` unici (senza distinzione maiuscole),
  email valida, al massimo 1000 dipendenti.

## Test

```bash
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
```
