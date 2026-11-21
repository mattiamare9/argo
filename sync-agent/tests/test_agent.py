import dataclasses

import httpx
import pytest

from argo_agent.client import SendError
from argo_agent.config import load_config
from argo_agent.main import run_cycle
from argo_agent.models import SourceError
from argo_agent.sources import ExcelSource

from .conftest import GOOD, make_xlsx

HB = 3600


def test_valid_file(cfg, source):
    make_xlsx(cfg.excel_path)
    recs = source.read()
    assert [(r.employee_id, r.status) for r in recs] == [("E001", "ACTIVE"), ("E002", "INACTIVE")]
    assert recs[0].email == "mario@azienda.it"


def test_numeric_ids_and_blank_rows(cfg, source):
    make_xlsx(
        cfg.excel_path,
        [[1001.0, "a@b.it", "A", "B", "ATTIVO"], [None] * 5, [1002, "c@d.it", "C", "D", "ATTIVO"]],
    )
    assert [r.employee_id for r in source.read()] == ["1001", "1002"]


def test_lock_files_ignored(cfg, source, tmp_path):
    make_xlsx(cfg.excel_path)
    (tmp_path / "~$emp.xlsx").write_bytes(b"garbage")
    assert len(source.read()) == 2
    locked = ExcelSource(dataclasses.replace(cfg, excel_path=tmp_path / "~$emp.xlsx"))
    with pytest.raises(SourceError):
        locked.read()


def bad(i, value):
    row = list(GOOD[0])
    row[i] = value
    return [row]


FAILURES = {
    "empty": dict(rows=[]),
    "missing_col": dict(header=["employee_id", "email", "first_name", "last_name"]),
    "dup_id": dict(rows=[GOOD[0], ["e001", "z@azienda.it", "Z", "Z", "ATTIVO"]]),
    "dup_email": dict(rows=[GOOD[0], ["E9", "MARIO@azienda.it", "Z", "Z", "ATTIVO"]]),
    "empty_field": dict(rows=bad(2, None)),
    "bad_status": dict(rows=bad(4, "BOH")),
    "bad_email": dict(rows=bad(1, "mario.azienda.it")),
    "bad_email2": dict(rows=bad(1, "mario@azienda")),
    "too_many": dict(rows=[[f"E{i}", f"u{i}@a.it", "A", "B", "ATTIVO"] for i in range(1001)]),
}


@pytest.mark.parametrize("name", FAILURES)
def test_validation_failures_reported_not_sent(name, cfg, source, client, store, api):
    make_xlsx(cfg.excel_path, **FAILURES[name])
    with pytest.raises(SourceError):
        source.read()
    run_cycle(source, client, store, HB)
    assert api.snapshots == []
    assert api.statuses[0]["ok"] is False and api.statuses[0]["message"]


def test_row_numbers_in_messages(cfg, source):
    make_xlsx(cfg.excel_path, rows=[GOOD[0], ["E2", "b@c.it", "", "X", "ATTIVO"]])
    with pytest.raises(SourceError, match="Riga 3"):
        source.read()
    make_xlsx(cfg.excel_path, rows=bad(4, "BOH"))
    with pytest.raises(SourceError, match="Riga 2.*BOH"):
        source.read()


def test_missing_and_corrupt_file(cfg, source, client, store, api):
    with pytest.raises(SourceError, match="non trovato"):
        source.read()
    cfg.excel_path.write_bytes(b"not an xlsx")
    with pytest.raises(SourceError, match="corrotto"):
        source.read()
    run_cycle(source, client, store, HB)
    assert api.snapshots == [] and api.statuses[0]["ok"] is False


def test_unchanged_not_resent_until_heartbeat_changed_resent(cfg, source, client, store, api):
    make_xlsx(cfg.excel_path)
    clock = [1000.0]
    now = lambda: clock[0]  # noqa: E731
    run_cycle(source, client, store, HB, now)
    run_cycle(source, client, store, HB, now)
    assert len(api.snapshots) == 1
    clock[0] += HB + 1
    run_cycle(source, client, store, HB, now)
    assert len(api.snapshots) == 2
    make_xlsx(cfg.excel_path, rows=[GOOD[0]])
    run_cycle(source, client, store, HB, now)
    assert len(api.snapshots) == 3 and len(api.snapshots[2]["records"]) == 1


def test_network_error_retries_same_snapshot_id(cfg, source, store):
    from argo_agent.client import ArgoClient

    make_xlsx(cfg.excel_path)
    calls, sleeps = [], []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            raise httpx.ConnectError("down")
        return httpx.Response(200, json={"status": "applied"})

    c = ArgoClient("https://x", "k", "excel-hr", httpx.MockTransport(handler), sleeps.append)
    run_cycle(source, c, store, HB)
    ids = {r.content for r in calls}
    assert len(calls) == 3 and len(ids) == 1
    assert sleeps == [1, 2]
    assert store.load().hash


def test_network_error_gives_up_after_retries():
    from argo_agent.client import ArgoClient

    sleeps = []

    def handler(request):
        raise httpx.ConnectError("down")

    c = ArgoClient("https://x", "k", "s", httpx.MockTransport(handler), sleeps.append)
    with pytest.raises(SendError):
        c.send_snapshot([])
    assert sleeps == [1, 2, 4]


def test_422_does_not_update_state(cfg, source, client, store, api):
    make_xlsx(cfg.excel_path)
    api.snapshot_response = lambda: httpx.Response(422, json={"detail": "dup"})
    run_cycle(source, client, store, HB)
    assert len(api.snapshots) == 1 and store.load().hash is None


@pytest.mark.parametrize("status", ["pending_confirmation", "duplicate"])
def test_accepted_statuses_update_state(status, cfg, source, client, store, api):
    make_xlsx(cfg.excel_path)
    api.snapshot_response = lambda: httpx.Response(200, json={"status": status})
    run_cycle(source, client, store, HB)
    assert store.load().hash


@pytest.mark.parametrize("content", [None, "{broken"])
def test_missing_or_corrupt_state_full_send(content, cfg, source, client, store, api):
    make_xlsx(cfg.excel_path)
    run_cycle(source, client, store, HB)
    if content is None:
        store.path.unlink()
    else:
        store.path.write_text(content)
    run_cycle(source, client, store, HB)
    assert len(api.snapshots) == 2


def test_column_mapping_and_custom_status(tmp_path, monkeypatch, api):
    make_xlsx(
        tmp_path / "e.xlsx",
        rows=[["7", "a@b.it", "A", "B", "Si"], ["8", "c@d.it", "C", "D", "No"]],
        header=["Matricola", "Mail", "Nome", "Cognome", "Stato"],
    )
    (tmp_path / "a.toml").write_text(
        f'api_url = "https://x/"\nexcel_path = "{tmp_path / "e.xlsx"}"\nstable_seconds = 0\n'
        '[columns]\nemployee_id="Matricola"\nemail="Mail"\nfirst_name="Nome"\n'
        'last_name="Cognome"\nstatus="Stato"\n[status_values]\nactive=["si"]\ninactive=["no"]\n'
    )
    monkeypatch.setenv("ARGO_AGENT_API_KEY", "secret")
    cfg = load_config(tmp_path / "a.toml")
    assert cfg.api_key == "secret" and cfg.api_url == "https://x"
    recs = ExcelSource(cfg).read()
    assert [(r.employee_id, r.status) for r in recs] == [("7", "ACTIVE"), ("8", "INACTIVE")]


def test_api_key_required(tmp_path, monkeypatch):
    from argo_agent.config import ConfigError

    (tmp_path / "a.toml").write_text('api_url = "https://x"\nexcel_path = "e.xlsx"\n')
    monkeypatch.delenv("ARGO_AGENT_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_config(tmp_path / "a.toml")
