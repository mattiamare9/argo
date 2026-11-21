"""Connettore SCIM 2.0 (RFC 7643/7644)."""

from typing import Any

import httpx

from app.modules.connectors.ports import AppAccount
from app.modules.jobs import ManualActionRequired, PermanentError

USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


class ScimConnector:
    def __init__(self, base_url: str, token: str, http: httpx.AsyncClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/scim+json",
        }

    async def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = await self.http.request(
            method, f"{self.base_url}{path}", headers=self.headers, **kwargs
        )
        if response.status_code in (401, 403):
            raise PermanentError(
                f"SCIM ha rifiutato le credenziali (HTTP {response.status_code}): "
                "controlla il token dell'applicazione"
            )
        return response

    async def _search(self, attribute: str, value: str) -> str | None:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        response = await self._send(
            "GET", "/Users", params={"filter": f'{attribute} eq "{escaped}"'}
        )
        response.raise_for_status()
        resources = response.json().get("Resources") or []
        return resources[0]["id"] if resources else None

    async def _find_id(self, account: AppAccount) -> str | None:
        # Prima externalId (= employee_id, stabile); poi userName, che cambia con l'email.
        return await self._search("externalId", account.employee_id) or await self._search(
            "userName", account.email
        )

    async def _set_active(self, user_id: str, active: bool) -> httpx.Response:
        body = {
            "schemas": [PATCH_SCHEMA],
            "Operations": [{"op": "replace", "path": "active", "value": active}],
        }
        return await self._send("PATCH", f"/Users/{user_id}", json=body)

    async def provision(self, account: AppAccount) -> None:
        user_id = await self._find_id(account)
        if user_id is not None:
            (await self._set_active(user_id, True)).raise_for_status()
            return
        body = {
            "schemas": [USER_SCHEMA],
            "userName": account.email,
            "name": {"givenName": account.first_name, "familyName": account.last_name},
            "emails": [{"value": account.email, "primary": True}],
            "externalId": account.employee_id,
            "active": True,
        }
        (await self._send("POST", "/Users", json=body)).raise_for_status()

    async def deprovision(self, account: AppAccount) -> None:
        user_id = await self._find_id(account)
        if user_id is None:
            # Non trovato non vuol dire chiuso (es. account creato a mano con altri dati).
            raise ManualActionRequired(
                f"Nessun account trovato per {account.email} ({account.employee_id}): "
                "verifica a mano che sia chiuso, poi premi Fatto."
            )
        response = await self._set_active(user_id, False)
        if response.status_code != 404:  # sparito nel frattempo: obiettivo raggiunto
            response.raise_for_status()
