import json

import httpx
import pytest
from openpyxl import Workbook

from argo_agent.client import ArgoClient
from argo_agent.config import Config
from argo_agent.sources import ExcelSource
from argo_agent.state import StateStore

HEADER = ["employee_id", "email", "first_name", "last_name", "status"]
GOOD = [
    ["E001", "mario@azienda.it", "Mario", "Rossi", "ATTIVO"],
    ["E002", "anna@azienda.it", "Anna", "Verdi", "inattivo "],
]


def make_xlsx(path, rows=GOOD, header=HEADER):
    wb = Workbook()
    ws = wb.active
    if header is not None:
        ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


class Api:
    """Fake backend recording requests; `handler` can be replaced per test."""

    def __init__(self):
        self.snapshots = []
        self.statuses = []
        self.snapshot_response = lambda: httpx.Response(200, json={"status": "applied"})

    def __call__(self, request):
        body = json.loads(request.content)
        if request.url.path.endswith("/snapshots"):
            self.snapshots.append(body)
            return self.snapshot_response()
        self.statuses.append(body)
        return httpx.Response(204)


@pytest.fixture
def api():
    return Api()


@pytest.fixture
def cfg(tmp_path):
    return Config(
        api_url="https://x",
        api_key="k",
        excel_path=tmp_path / "emp.xlsx",
        stable_seconds=0,
        state_dir=tmp_path / "state",
    )


@pytest.fixture
def source(cfg):
    return ExcelSource(cfg, sleep=lambda s: None)


@pytest.fixture
def client(api):
    return ArgoClient("https://x", "k", "excel-hr", httpx.MockTransport(api), lambda s: None)


@pytest.fixture
def store(cfg):
    return StateStore(cfg.state_dir)
