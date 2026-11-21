import argparse
import logging
import time
from collections.abc import Callable

from .client import ArgoClient, SendError
from .config import ConfigError, load_config
from .models import SourceError, SourceReader
from .sources import ExcelSource
from .state import State, StateStore, snapshot_hash

log = logging.getLogger("argo_agent")
ACCEPTED = {"applied", "pending_confirmation", "duplicate"}


def run_cycle(
    source: SourceReader,
    client: ArgoClient,
    store: StateStore,
    heartbeat_seconds: float,
    now: Callable[[], float] = time.time,
) -> None:
    try:
        records = source.read()
    except SourceError as exc:
        log.error("Lettura fonte fallita, sincronizzazione sospesa: %s", exc)
        client.report_status(False, str(exc))
        return
    digest = snapshot_hash(records)
    state = store.load()
    if (
        digest == state.hash
        and state.last_sent_at is not None
        and now() - state.last_sent_at < heartbeat_seconds
    ):
        log.info("Nessuna modifica (%d dipendenti), nulla da inviare", len(records))
        return
    try:
        result = client.send_snapshot(records)
    except SendError as exc:
        log.error("Invio fallito, stato non aggiornato: %s", exc)
        return
    status = result.get("status")
    if status in ACCEPTED:
        store.save(State(hash=digest, last_sent_at=now()))
        log.info(
            "Snapshot inviato: %d dipendenti, esito %s, riepilogo %s",
            len(records),
            status,
            result.get("summary"),
        )
    else:
        log.error("Esito sconosciuto dal backend: %s", status)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argo_agent")
    parser.add_argument("--config", default="agent.toml")
    parser.add_argument("--once", action="store_true", help="esegue un solo ciclo ed esce")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        log.error("%s", exc)
        return 2
    source = ExcelSource(cfg)
    client = ArgoClient(cfg.api_url, cfg.api_key, cfg.source_name)
    store = StateStore(cfg.state_dir)
    while True:
        try:
            run_cycle(source, client, store, cfg.heartbeat_seconds)
        except Exception:
            log.exception("Errore imprevisto nel ciclo")
        if args.once:
            return 0
        time.sleep(cfg.poll_seconds)
