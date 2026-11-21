"""Connettori verso le applicazioni: porta e adapter (manuale, SCIM 2.0)."""

from app.modules.connectors.manual import ManualConnector
from app.modules.connectors.ports import AppAccount, AppConnector
from app.modules.connectors.scim import ScimConnector
from app.modules.connectors.service import build_connector

__all__ = ["AppAccount", "AppConnector", "ManualConnector", "ScimConnector", "build_connector"]
