"""Worker dei job: uv run python -m app.worker (stessa immagine dell'API, ADR-006)."""

import asyncio
import logging
import signal

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import create_engine
from app.modules import jobs, provisioning
from app.modules.identity import build_identity_provider

logger = logging.getLogger("app.worker")
IDLE_POLL_SECONDS = 2.0


async def run(stop: asyncio.Event) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with httpx.AsyncClient(timeout=15) as http:
        handlers = provisioning.build_handlers(
            build_identity_provider(settings, http), maker, settings, http
        )
        logger.info("worker avviato: %d tipi di job", len(handlers))
        while not stop.is_set():
            try:
                async with maker() as db:
                    worked = await jobs.run_once(db, handlers)
            except Exception:  # DB momentaneamente irraggiungibile: aspetta e riprova
                logger.exception("ciclo del worker fallito")
                worked = False
            if not worked:
                try:
                    await asyncio.wait_for(stop.wait(), IDLE_POLL_SECONDS)
                except TimeoutError:
                    pass
    await engine.dispose()
    logger.info("worker fermato")


def main() -> None:
    configure_logging(get_settings().log_level)

    async def _main() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        await run(stop)

    asyncio.run(_main())


if __name__ == "__main__":
    main()
