import dataclasses
import logging

import httpx
import pytest

from argo_agent.config import ConfigError, load_config
from argo_agent.main import run_cycle
from argo_agent.models import SourceError
from argo_agent.sources import EduplanSource

LOGIN_PAGE = '<form><input name="__RequestVerificationToken" type="hidden" value="tok123" /></form>'


def user(id, email, nome="Mario", cognome="Rossi", attivo=True, username=None):
    return {
        "Id": id,
        "UserName": username or f"u{id}",
        "Email": email,
        "Nome": nome,
        "Cognome": cognome,
        "Attivo": attivo,
    }


class Eduplan:
    """Fake EduPLANWeb: login form, then the users endpoint used by the Users page."""

    def __init__(self, users, password="giusta"):
        self.users = users
        self.password = password
        self.logins = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/Account/Login" and request.method == "GET":
            return httpx.Response(200, text=LOGIN_PAGE)
        if path == "/Account/Login":
            form = dict(httpx.QueryParams(request.content.decode()))
            self.logins.append(form)
            if (
                form.get("__RequestVerificationToken") != "tok123"
                or form["Password"] != self.password
            ):
                return httpx.Response(200, text=LOGIN_PAGE)
            return httpx.Response(
                302, headers={"Location": "/Dashboard/MyDashboard", "Set-Cookie": "auth=1; Path=/"}
            )
        if path == "/Dashboard/MyDashboard":
            return httpx.Response(200, text="ok")
        if path == "/Configurazione/ReadUsers":
            if request.headers.get("cookie") != "auth=1":
                return httpx.Response(404)
            assert dict(httpx.QueryParams(request.content.decode()))["includiDisattivi"] == "true"
            assert request.url.params["tenantId"] == "1"
            return httpx.Response(200, json={"Data": self.users, "Total": len(self.users)})
        return httpx.Response(404)


@pytest.fixture
def edu_cfg(cfg):
    return dataclasses.replace(
        cfg,
        source="eduplan",
        eduplan_url="https://edu.example.it",
        eduplan_username="automazione@x.it",
        eduplan_password="giusta",
    )


def read(cfg, users, **kw):
    fake = Eduplan(users, **kw)
    return EduplanSource(cfg, httpx.MockTransport(fake)).read(), fake


def test_reads_active_and_inactive_with_stable_id(edu_cfg):
    records, fake = read(
        edu_cfg,
        [user(7, "mario@x.it"), user(9, "anna@x.it", "Anna", "Verdi", attivo=False)],
    )
    assert [(r.employee_id, r.email, r.first_name, r.last_name, r.status) for r in records] == [
        ("7", "mario@x.it", "Mario", "Rossi", "ACTIVE"),
        ("9", "anna@x.it", "Anna", "Verdi", "INACTIVE"),
    ]
    assert fake.logins[0]["Username"] == "automazione@x.it"


def test_unusable_accounts_skipped_and_logged(edu_cfg, caplog):
    caplog.set_level(logging.WARNING)
    records, _ = read(
        edu_cfg,
        [
            user(1, "ok@x.it"),
            user(2, "servizio@x.it", "Aula", ""),  # account di servizio senza cognome
            user(3, "non-una-email"),
            user(4, "doppia@x.it"),  # due attivi con la stessa email: nessuno dei due
            user(5, "DOPPIA@x.it"),
            user(6, "rifatto@x.it", attivo=False),  # account rifatto: vale l'unico attivo
            user(8, "rifatto@x.it"),
        ],
    )
    assert sorted(r.employee_id for r in records) == ["1", "8"]
    skipped = caplog.text
    for fragment in (
        "account 2 (u2) escluso: campi vuoti: Cognome",
        "account 3",
        "account 4",
        "account 5",
        "account 6",
    ):
        assert fragment in skipped


def test_wrong_password_is_a_source_error(edu_cfg):
    with pytest.raises(SourceError, match="Login a EduPLANWeb rifiutato"):
        read(edu_cfg, [user(1, "a@x.it")], password="altra")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>pagina cambiata</html>"),
        httpx.Response(200, json={"Errore": "x"}),
        httpx.Response(500),
    ],
)
def test_changed_or_failing_site_is_a_source_error(edu_cfg, response):
    def handler(request):
        if request.url.path == "/Configurazione/ReadUsers":
            return response
        return fake(request)

    fake = Eduplan([user(1, "a@x.it")])
    with pytest.raises(SourceError):
        EduplanSource(edu_cfg, httpx.MockTransport(handler)).read()


def test_missing_token_and_network_error(edu_cfg):
    no_token = httpx.MockTransport(lambda r: httpx.Response(200, text="<form></form>"))
    with pytest.raises(SourceError, match="token non trovato"):
        EduplanSource(edu_cfg, no_token).read()

    def down(request):
        raise httpx.ConnectError("rifiutata")

    with pytest.raises(SourceError, match="non raggiungibile"):
        EduplanSource(edu_cfg, httpx.MockTransport(down)).read()


def test_failure_reported_to_argo_not_sent(edu_cfg, client, store, api):
    source = EduplanSource(edu_cfg, httpx.MockTransport(Eduplan([], password="altra")))
    run_cycle(source, client, store, 3600)
    assert api.snapshots == []
    assert api.statuses[0]["ok"] is False


def test_config_needs_url_and_credentials_from_env(tmp_path, monkeypatch):
    path = tmp_path / "agent.toml"
    path.write_text(
        'source = "eduplan"\napi_url = "http://api:8000"\neduplan_url = "https://e.it/"\n'
    )
    monkeypatch.setenv("ARGO_AGENT_API_KEY", "k")
    with pytest.raises(ConfigError, match="EDUPLAN_USERNAME"):
        load_config(path)
    monkeypatch.setenv("EDUPLAN_USERNAME", "u")
    monkeypatch.setenv("EDUPLAN_PASSWORD", "segretissima")
    cfg = load_config(path)
    assert (cfg.source, cfg.eduplan_url, cfg.excel_path) == ("eduplan", "https://e.it", None)
    assert cfg.eduplan_password == "segretissima"
    assert "segretissima" not in repr(cfg)  # password fuori da log e traceback
