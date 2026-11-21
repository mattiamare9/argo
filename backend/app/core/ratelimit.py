"""Rate limiting in memoria, finestra scorrevole per chiave (IP del client)."""

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status


class RateLimiter:
    # shortcut: stato in memoria valido solo con un unico processo API (produzione); con più
    # repliche i limiti si moltiplicano, a quel punto spostare i contatori su Redis/Postgres.
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window: float = 60.0) -> float | None:
        """Registra una richiesta; None se ammessa, altrimenti i secondi da attendere."""
        now = self._clock()
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return hits[0] + window - now
        hits.append(now)
        return None


def client_ip(request: Request) -> str:
    # X-Forwarded-For è affidabile solo perché l'API è raggiungibile unicamente attraverso Caddy
    # (nessuna porta pubblicata, deploy/compose.prod.yaml), che accoda l'IP del client: si usa
    # l'ultima voce, l'unica non falsificabile dal client.
    forwarded = request.headers.get("X-Forwarded-For", "")
    last = forwarded.rsplit(",", 1)[-1].strip()
    return last or (request.client.host if request.client else "unknown")


def rate_limit(scope: str, setting: str) -> Callable[[Request], None]:
    """Dipendenza FastAPI: `setting` è il nome dell'impostazione con il limite al minuto."""

    def dependency(request: Request) -> None:
        settings = request.app.state.settings
        if not settings.ratelimit_enabled:
            return
        retry_after = request.app.state.limiter.check(
            f"{scope}:{client_ip(request)}", getattr(settings, setting)
        )
        if retry_after is not None:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Troppe richieste: riprova tra poco",
                headers={"Retry-After": str(max(1, int(retry_after) + 1))},
            )

    return dependency


limit_auth = rate_limit("auth", "ratelimit_auth_per_minute")
limit_agent = rate_limit("agent", "ratelimit_agent_per_minute")
