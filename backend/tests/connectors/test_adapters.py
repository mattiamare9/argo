import json

import httpx
import pytest

from app.modules.connectors import AppAccount, ManualConnector, ScimConnector
from app.modules.jobs import ManualActionRequired, PermanentError

ACCOUNT = AppAccount("E001", "mario.rossi@x.it", "Mario", "Rossi")
USER = "urn:ietf:params:scim:schemas:core:2.0:User"
PATCH = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


def scim(handler) -> tuple[ScimConnector, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(record))
    return ScimConnector("https://app.test/scim/v2/", "tok", http), seen


def found(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"Resources": [{"id": "u1"}]})


def empty(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"Resources": []})


async def test_provision_creates_missing_user() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return empty(request) if request.method == "GET" else httpx.Response(201, json={})

    connector, seen = scim(handler)
    await connector.provision(ACCOUNT)
    by_external_id, get, post = seen
    assert by_external_id.url.params["filter"] == 'externalId eq "E001"'
    assert get.url.path == "/scim/v2/Users"
    assert get.url.params["filter"] == 'userName eq "mario.rossi@x.it"'
    assert get.headers["Authorization"] == "Bearer tok"
    assert post.method == "POST"
    assert json.loads(post.content) == {
        "schemas": [USER],
        "userName": "mario.rossi@x.it",
        "name": {"givenName": "Mario", "familyName": "Rossi"},
        "emails": [{"value": "mario.rossi@x.it", "primary": True}],
        "externalId": "E001",
        "active": True,
    }


async def test_provision_reactivates_existing_user() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return found(request) if request.method == "GET" else httpx.Response(200, json={})

    connector, seen = scim(handler)
    await connector.provision(ACCOUNT)
    assert [r.method for r in seen] == ["GET", "PATCH"]
    assert seen[1].url.path == "/scim/v2/Users/u1"
    assert json.loads(seen[1].content)["Operations"] == [
        {"op": "replace", "path": "active", "value": True}
    ]


async def test_deprovision_patches_active_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return found(request) if request.method == "GET" else httpx.Response(200, json={})

    connector, seen = scim(handler)
    await connector.deprovision(ACCOUNT)
    assert seen[1].method == "PATCH"
    assert seen[1].url.path == "/scim/v2/Users/u1"
    assert json.loads(seen[1].content) == {
        "schemas": [PATCH],
        "Operations": [{"op": "replace", "path": "active", "value": False}],
    }


async def test_deprovision_missing_user_needs_manual_check() -> None:
    from app.modules.jobs import ManualActionRequired

    connector, seen = scim(empty)
    with pytest.raises(ManualActionRequired):
        await connector.deprovision(ACCOUNT)
    assert [r.method for r in seen] == ["GET", "GET"]  # externalId, poi userName


@pytest.mark.parametrize("code", [401, 403])
async def test_rejected_credentials_are_permanent(code: int) -> None:
    connector, _ = scim(lambda r: httpx.Response(code))
    with pytest.raises(PermanentError):
        await connector.provision(ACCOUNT)


async def test_server_error_is_retryable() -> None:
    connector, _ = scim(lambda r: httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await connector.deprovision(ACCOUNT)


async def test_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("giù")

    connector, _ = scim(handler)
    with pytest.raises(httpx.ConnectError):
        await connector.provision(ACCOUNT)


async def test_manual_connector_asks_for_a_human() -> None:
    connector = ManualConnector("FatturaFacile")
    with pytest.raises(ManualActionRequired, match="Disattiva a mano.*mario.rossi@x.it.*Fatto"):
        await connector.deprovision(ACCOUNT)
    with pytest.raises(ManualActionRequired, match="Crea a mano"):
        await connector.provision(ACCOUNT)
