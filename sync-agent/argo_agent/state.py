import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .models import EmployeeRecord


def snapshot_hash(records: list[EmployeeRecord]) -> str:
    ordered = sorted((r.to_dict() for r in records), key=lambda d: d["employee_id"].lower())
    canonical = json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class State:
    hash: str | None = None
    last_sent_at: float | None = None  # epoch seconds of the last accepted send


class StateStore:
    def __init__(self, state_dir: Path) -> None:
        self.path = state_dir / "state.json"

    def load(self) -> State:
        """Missing or corrupt state means a full send, which is harmless (backend is idempotent)."""
        try:
            data = json.loads(self.path.read_text())
            return State(hash=str(data["hash"]), last_sent_at=float(data["last_sent_at"]))
        except (OSError, ValueError, KeyError, TypeError):
            return State()

    def save(self, state: State) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump({"hash": state.hash, "last_sent_at": state.last_sent_at}, f)
        os.replace(tmp, self.path)
