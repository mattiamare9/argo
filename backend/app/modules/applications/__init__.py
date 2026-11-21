"""Registro delle applicazioni i cui account sono gestiti da Argo."""

from app.modules.applications.models import Application
from app.modules.applications.service import get_application, list_enabled

__all__ = ["Application", "get_application", "list_enabled"]
