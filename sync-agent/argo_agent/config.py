import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

FIELDS = ("employee_id", "email", "first_name", "last_name", "status")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    api_url: str
    api_key: str
    excel_path: Path | None = None
    source_name: str = "excel-hr"
    source: str = "excel"  # "excel" | "eduplan"
    eduplan_url: str = ""
    eduplan_tenant_id: int = 1
    eduplan_username: str = ""
    eduplan_password: str = field(default="", repr=False)
    sheet: str | None = None
    columns: dict[str, str] = field(default_factory=lambda: {f: f for f in FIELDS})
    active_values: tuple[str, ...] = ("ATTIVO",)
    inactive_values: tuple[str, ...] = ("INATTIVO",)
    poll_seconds: float = 60
    heartbeat_seconds: float = 3600
    stable_seconds: float = 10
    state_dir: Path = Path(".argo-agent-state")


def load_config(path: str | Path) -> Config:
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Impossibile leggere la configurazione {path}: {exc}") from exc
    api_key = os.environ.get("ARGO_AGENT_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("Variabile d'ambiente ARGO_AGENT_API_KEY mancante")
    source = raw.get("source", "excel")
    if source not in ("excel", "eduplan"):
        raise ConfigError(f"Fonte sconosciuta: {source} (excel o eduplan)")
    for required in ("api_url", "excel_path" if source == "excel" else "eduplan_url"):
        if not raw.get(required):
            raise ConfigError(f"Parametro obbligatorio mancante nella configurazione: {required}")
    # Credenziali del gestionale solo dall'ambiente, come la chiave API.
    eduplan_username = os.environ.get("EDUPLAN_USERNAME", "").strip()
    eduplan_password = os.environ.get("EDUPLAN_PASSWORD", "")
    if source == "eduplan" and not (eduplan_username and eduplan_password):
        raise ConfigError("Variabili d'ambiente EDUPLAN_USERNAME e EDUPLAN_PASSWORD mancanti")
    columns = {f: f for f in FIELDS} | raw.get("columns", {})
    unknown = set(columns) - set(FIELDS)
    if unknown:
        raise ConfigError(f"Campi sconosciuti in [columns]: {', '.join(sorted(unknown))}")
    values = raw.get("status_values", {})
    return Config(
        api_url=raw["api_url"].rstrip("/"),
        api_key=api_key,
        excel_path=Path(raw["excel_path"]) if raw.get("excel_path") else None,
        source_name=raw.get("source_name", "excel-hr"),
        source=source,
        eduplan_url=raw.get("eduplan_url", "").rstrip("/"),
        eduplan_tenant_id=raw.get("eduplan_tenant_id", 1),
        eduplan_username=eduplan_username,
        eduplan_password=eduplan_password,
        sheet=raw.get("sheet"),
        columns=columns,
        active_values=tuple(values.get("active", ["ATTIVO"])),
        inactive_values=tuple(values.get("inactive", ["INATTIVO"])),
        poll_seconds=raw.get("poll_seconds", 60),
        heartbeat_seconds=raw.get("heartbeat_seconds", 3600),
        stable_seconds=raw.get("stable_seconds", 10),
        state_dir=Path(raw.get("state_dir", ".argo-agent-state")),
    )
