"""EduPLANWeb: gestionale web senza API. Login con il form del sito, poi lettura degli utenti
dallo stesso endpoint JSON che riempie la tabella Configurazione → Users (e il suo export
Excel). L'endpoint dà più dell'Excel: l'`Id` stabile e anche gli account disattivati."""

import logging
import re
from collections import defaultdict

import httpx

from ..config import Config
from ..models import EmployeeRecord, SourceError
from ..validation import build_records, valid_email

log = logging.getLogger("argo_agent")
TOKEN = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')


class EduplanSource:
    def __init__(self, config: Config, transport: httpx.BaseTransport | None = None) -> None:
        self.config = config
        self._transport = transport

    def read(self) -> list[EmployeeRecord]:
        cfg = self.config
        try:
            with httpx.Client(
                base_url=cfg.eduplan_url,
                follow_redirects=True,
                timeout=30,
                transport=self._transport,
            ) as http:
                users = self._fetch(http)
        except httpx.HTTPError as exc:
            raise SourceError(f"EduPLANWeb non raggiungibile: {exc}") from exc
        return to_records(users)

    def _fetch(self, http: httpx.Client) -> list[dict]:
        cfg = self.config
        token = TOKEN.search(http.get("/Account/Login").raise_for_status().text)
        if not token:
            raise SourceError("Pagina di login di EduPLANWeb cambiata: token non trovato")
        resp = http.post(
            "/Account/Login",
            data={
                "Username": cfg.eduplan_username,
                "Password": cfg.eduplan_password,
                "RememberMe": "false",
                "ReturnUrl": "/",
                "__RequestVerificationToken": token.group(1),
            },
        ).raise_for_status()
        if resp.url.path.lower().startswith("/account/login"):  # rimandati al form: rifiutato
            raise SourceError("Login a EduPLANWeb rifiutato: controlla utente e password")
        resp = http.post(
            "/Configurazione/ReadUsers",
            params={"tenantId": cfg.eduplan_tenant_id},
            data={"sort": "", "group": "", "filter": "", "includiDisattivi": "true"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        ).raise_for_status()
        try:
            users = resp.json()["Data"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SourceError(
                "Risposta di EduPLANWeb cambiata: elenco utenti non leggibile"
            ) from exc
        if not isinstance(users, list):
            raise SourceError("Risposta di EduPLANWeb cambiata: elenco utenti non leggibile")
        return users


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def to_records(users: list[dict]) -> list[EmployeeRecord]:
    """Account non utilizzabili esclusi (e scritti nel log) invece di bloccare tutto: chi manca
    dallo snapshot non viene mai disattivato dal backend, quindi escludere è prudente."""
    usable: list[dict] = []
    for u in users:
        missing = [k for k in ("Id", "Email", "Nome", "Cognome") if not _text(u.get(k))]
        if missing:
            _skip(u, f"campi vuoti: {', '.join(missing)}")
        elif not valid_email(_text(u["Email"])):
            _skip(u, "email non valida")
        else:
            usable.append(u)
    by_email: dict[str, list[dict]] = defaultdict(list)
    for u in usable:
        by_email[_text(u["Email"]).lower()].append(u)
    rows = []
    for group in by_email.values():
        active = [u for u in group if u.get("Attivo") is True]
        # Stessa email su più account: vale l'unico attivo (account rifatto); altrimenti nessuno.
        keep = group if len(group) == 1 else active if len(active) == 1 else []
        for u in group:
            if u not in keep:
                _skip(u, "email usata da più account")
        for u in keep:
            row = {
                "employee_id": _text(u["Id"]),
                "email": _text(u["Email"]),
                "first_name": _text(u["Nome"]),
                "last_name": _text(u["Cognome"]),
                "status": "attivo" if u.get("Attivo") is True else "disattivo",
            }
            rows.append((len(rows) + 1, row))
    return build_records(rows, ("attivo",), ("disattivo",))


def _skip(user: dict, reason: str) -> None:
    log.warning(
        "EduPLANWeb: account %s (%s) escluso: %s",
        _text(user.get("Id")) or "?",
        _text(user.get("UserName")) or "?",
        reason,
    )
