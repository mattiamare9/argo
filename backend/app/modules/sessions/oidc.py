"""Client OIDC minimo per il BFF: Authorization Code Flow + PKCE (S256).

I token arrivano dal token endpoint via back-channel autenticato (client secret), quindi
l'ID token è validato sui claims (iss, aud, exp, nonce) senza verifica della firma, come
consentito da OpenID Connect Core 1.0 §3.1.3.7 punto 6. Vedi ADR-022.
"""

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx


class OidcError(Exception):
    pass


@dataclass(frozen=True)
class OidcConfig:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def decode_claims(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError) as exc:
        raise OidcError("token non leggibile") from exc


def validate_id_token(claims: dict[str, Any], config: OidcConfig, nonce: str) -> None:
    aud = claims.get("aud")
    audiences = aud if isinstance(aud, list) else [aud]
    if claims.get("iss") != config.issuer:
        raise OidcError("issuer non valido")
    if config.client_id not in audiences:
        raise OidcError("audience non valida")
    if claims.get("exp", 0) < time.time():
        raise OidcError("ID token scaduto")
    if claims.get("nonce") != nonce:
        raise OidcError("nonce non valido")


class OidcClient:
    def __init__(self, config: OidcConfig, http: httpx.AsyncClient) -> None:
        self.config = config
        self._http = http
        self._metadata: dict[str, Any] | None = None

    async def _get_metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            url = f"{self.config.issuer}/.well-known/openid-configuration"
            try:
                response = await self._http.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise OidcError(f"identity provider non raggiungibile: {exc}") from exc
            self._metadata = response.json()
        return self._metadata

    async def authorization_url(self, state: str, nonce: str, code_challenge: str) -> str:
        endpoint = (await self._get_metadata())["authorization_endpoint"]
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": "openid",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        endpoint = (await self._get_metadata())["token_endpoint"]
        try:
            response = await self._http.post(
                endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "code_verifier": code_verifier,
                },
                auth=(self.config.client_id, self.config.client_secret),
            )
        except httpx.HTTPError as exc:
            raise OidcError(f"identity provider non raggiungibile: {exc}") from exc
        if response.status_code != 200:
            raise OidcError(f"scambio del codice rifiutato (HTTP {response.status_code})")
        return response.json()

    async def end_session_url(self, post_logout_redirect_uri: str) -> str:
        endpoint = (await self._get_metadata())["end_session_endpoint"]
        params = {
            "client_id": self.config.client_id,
            "post_logout_redirect_uri": post_logout_redirect_uri,
        }
        return f"{endpoint}?{urlencode(params)}"
