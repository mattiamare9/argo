from app.modules.connectors.ports import AppAccount
from app.modules.jobs import ManualActionRequired


class ManualConnector:
    """App senza API: il job resta in MANUAL_PENDING finché una persona preme «Fatto»."""

    def __init__(self, app_name: str) -> None:
        self.app_name = app_name

    async def provision(self, account: AppAccount) -> None:
        raise ManualActionRequired(
            f"Crea a mano l'account di {account.email} su {self.app_name}, poi premi Fatto."
        )

    async def deprovision(self, account: AppAccount) -> None:
        raise ManualActionRequired(
            f"Disattiva a mano l'account di {account.email} su {self.app_name}, poi premi Fatto."
        )
