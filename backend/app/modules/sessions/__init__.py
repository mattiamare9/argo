"""Sessioni della dashboard (BFF OIDC). Interfaccia pubblica per gli altri moduli."""

from app.modules.sessions.dependencies import current_user, require_csrf, require_role
from app.modules.sessions.service import CurrentUser, revoke_for_subject

__all__ = ["CurrentUser", "current_user", "require_csrf", "require_role", "revoke_for_subject"]
