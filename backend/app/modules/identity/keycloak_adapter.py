"""Adapter Keycloak Admin REST API (verificato su 26.8.2, vedi docs/superpowers/plans)."""

import time
from typing import Any

import httpx

from app.modules.identity.ports import IdentityError, IdentityUser, UserNotFound

ENROLLMENT_ACTIONS = ["webauthn-register-passwordless"]
ENROLLMENT_LIFESPAN_SECONDS = 72 * 3600


class KeycloakIdentityProvider:
    def __init__(
        self,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        http: httpx.AsyncClient,
    ) -> None:
        self._token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
        self._admin = f"{base_url}/admin/realms/{realm}"
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def ensure_user(self, user: IdentityUser) -> None:
        profile = {"email": user.email, "firstName": user.first_name, "lastName": user.last_name}
        existing = await self._find(user.employee_id)
        if existing is None:
            body = {"username": user.employee_id, "enabled": True, "emailVerified": True, **profile}
            await self._request("POST", "/users", json=body)
        else:
            await self._request("PUT", f"/users/{existing['id']}", json=profile)

    async def set_enabled(self, employee_id: str, enabled: bool) -> None:
        uid = await self._require_id(employee_id)
        await self._request("PUT", f"/users/{uid}", json={"enabled": enabled})

    async def logout(self, employee_id: str) -> None:
        uid = await self._require_id(employee_id)
        await self._request("POST", f"/users/{uid}/logout")

    async def send_enrollment(self, employee_id: str) -> None:
        uid = await self._require_id(employee_id)
        await self._request(
            "PUT",
            f"/users/{uid}/execute-actions-email",
            params={"lifespan": ENROLLMENT_LIFESPAN_SECONDS},
            json=ENROLLMENT_ACTIONS,
        )

    async def grant_role(self, employee_id: str, role: str) -> None:
        uid = await self._require_id(employee_id)
        role_rep = (await self._request("GET", f"/roles/{role}")).json()
        await self._request("POST", f"/users/{uid}/role-mappings/realm", json=[role_rep])

    async def current_roles(self, username: str) -> frozenset[str] | None:
        user = await self._find(username)
        if user is None or not user.get("enabled", False):
            return None
        response = await self._request("GET", f"/users/{user['id']}/role-mappings/realm/composite")
        return frozenset(role["name"] for role in response.json())

    async def _find(self, employee_id: str) -> dict[str, Any] | None:
        try:
            response = await self._request(
                "GET", "/users", params={"username": employee_id, "exact": "true"}
            )
        except UserNotFound as exc:  # 404 sulla ricerca: realm o URL sbagliati
            raise IdentityError("ricerca utenti non disponibile: controlla il realm") from exc
        users = response.json()
        return users[0] if users else None

    async def _require_id(self, employee_id: str) -> str:
        user = await self._find(employee_id)
        if user is None:
            raise UserNotFound(employee_id)
        return user["id"]

    async def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        try:
            response = await self._http.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
        except httpx.HTTPError as exc:
            raise IdentityError(f"Keycloak non raggiungibile: {exc}") from exc
        if response.status_code != 200:
            raise IdentityError(f"token service account rifiutato (HTTP {response.status_code})")
        payload = response.json()
        self._token = payload["access_token"]
        # Margine di 30 s per non usare un token che scade durante la richiesta.
        self._token_expires_at = time.monotonic() + payload["expires_in"] - 30
        return self._token

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {"Authorization": f"Bearer {await self._access_token()}"}
        try:
            response = await self._http.request(
                method, f"{self._admin}{path}", headers=headers, **kwargs
            )
        except httpx.HTTPError as exc:
            raise IdentityError(f"Keycloak non raggiungibile: {exc}") from exc
        if response.status_code == 404:
            raise UserNotFound(path)
        if response.status_code >= 400:
            raise IdentityError(f"{method} {path}: HTTP {response.status_code}")
        return response
