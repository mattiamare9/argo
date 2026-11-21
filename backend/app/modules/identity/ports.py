from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IdentityUser:
    employee_id: str
    email: str
    first_name: str
    last_name: str


class IdentityError(Exception):
    """L'identity provider ha risposto con un errore o non è raggiungibile."""


class UserNotFound(IdentityError):
    pass


class IdentityProvider(Protocol):
    """Operazioni sul ciclo di vita delle identità. Tutte idempotenti."""

    async def ensure_user(self, user: IdentityUser) -> None:
        """Crea l'utente se manca, altrimenti aggiorna l'anagrafica senza toccare `enabled`."""

    async def set_enabled(self, employee_id: str, enabled: bool) -> None: ...

    async def logout(self, employee_id: str) -> None:
        """Chiude tutte le sessioni dell'utente sull'identity provider."""

    async def send_enrollment(self, employee_id: str) -> None:
        """Invia l'email per registrare una passkey."""

    async def grant_role(self, employee_id: str, role: str) -> None: ...

    async def current_roles(self, username: str) -> frozenset[str] | None:
        """Ruoli di realm attuali; None se l'utente non esiste o è disabilitato."""
