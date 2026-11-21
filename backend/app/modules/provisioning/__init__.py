"""Ciclo di vita: trasforma i cambi di anagrafica in passi eseguiti dal worker."""

from app.modules.provisioning.handlers import build_handlers
from app.modules.provisioning.service import RunOut, list_runs, on_changes

__all__ = ["RunOut", "build_handlers", "list_runs", "on_changes"]
