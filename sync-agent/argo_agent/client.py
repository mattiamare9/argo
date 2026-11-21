import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from .models import EmployeeRecord

log = logging.getLogger("argo_agent")
BACKOFF_SECONDS = (1, 2, 4)


class SendError(Exception):
    """The snapshot was not accepted; the state must not be updated."""


class ArgoClient:
    def __init__(
        self,
        api_url: str,
        api_key: str,
        source: str,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self._sleep = sleep
        self._http = httpx.Client(
            base_url=api_url,
            timeout=20,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def send_snapshot(self, records: list[EmployeeRecord]) -> dict:
        body = {
            "snapshot_id": str(uuid.uuid4()),
            "source": self.source,
            "read_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "records": [r.to_dict() for r in records],
        }
        resp = None
        for attempt in range(len(BACKOFF_SECONDS) + 1):  # same snapshot_id on every retry
            try:
                resp = self._http.post("/api/v1/sync/snapshots", json=body)
                break
            except httpx.TransportError as exc:
                if attempt == len(BACKOFF_SECONDS):
                    raise SendError(f"Errore di rete, invio abbandonato: {exc}") from exc
                delay = BACKOFF_SECONDS[attempt]
                log.warning("Errore di rete (%s), nuovo tentativo tra %ss", exc, delay)
                self._sleep(delay)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 401:
            log.error("Errore di configurazione: chiave API non valida o revocata (401)")
            raise SendError("401 non autorizzato")
        if resp.status_code == 422:
            detail = resp.json().get("detail") if resp.content else resp.text
            log.error("Snapshot rifiutato dal backend (422): %s", detail)
            raise SendError(f"422 snapshot rifiutato: {detail}")
        raise SendError(f"Risposta inattesa dal backend: {resp.status_code}")

    def report_status(self, ok: bool, message: str) -> None:
        try:
            resp = self._http.post("/api/v1/sync/agent-status", json={"ok": ok, "message": message})
            if resp.status_code != 204:
                log.warning("Segnalazione stato non accettata: HTTP %s", resp.status_code)
        except httpx.TransportError as exc:
            log.warning("Impossibile segnalare lo stato al backend: %s", exc)
