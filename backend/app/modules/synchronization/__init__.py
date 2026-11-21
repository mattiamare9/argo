"""Ricezione degli snapshot della fonte ufficiale dagli agent on-premise (docs/sync-api.md)."""

from app.modules.synchronization.service import create_agent

__all__ = ["create_agent"]
