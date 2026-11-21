import httpx

from app.core.config import Settings
from app.core.ratelimit import RateLimiter
from app.main import create_app


def test_window_slides_with_injected_clock() -> None:
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    assert [limiter.check("k", 2) for _ in range(2)] == [None, None]
    assert limiter.check("k", 2) == 60.0
    now[0] = 59.0
    assert limiter.check("k", 2) == 1.0
    now[0] = 60.0
    assert limiter.check("k", 2) is None


def test_keys_are_counted_separately() -> None:
    limiter = RateLimiter(clock=lambda: 0.0)
    assert limiter.check("1.1.1.1", 1) is None
    assert limiter.check("1.1.1.1", 1) is not None
    assert limiter.check("2.2.2.2", 1) is None


async def test_agent_endpoint_returns_429_with_retry_after(migrated_database: str) -> None:
    app = create_app(
        Settings(
            database_url=migrated_database, ratelimit_agent_per_minute=2, oidc_client_secret=None
        )
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

        async def post(ip: str) -> httpx.Response:
            # Le richieste senza chiave valida danno 401: il limite si applica comunque prima.
            return await client.post(
                "/api/v1/sync/agent-status",
                json={"ok": True, "message": ""},
                headers={"X-Forwarded-For": f"9.9.9.9, {ip}"},
            )

        assert [(await post("1.1.1.1")).status_code for _ in range(2)] == [401, 401]
        blocked = await post("1.1.1.1")
        assert blocked.status_code == 429
        assert 1 <= int(blocked.headers["Retry-After"]) <= 60
        assert "Troppe richieste" in blocked.json()["detail"]
        assert (await post("2.2.2.2")).status_code == 401  # un altro IP ha il suo conteggio
    await app.state.engine.dispose()
