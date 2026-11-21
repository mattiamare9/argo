import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from openpyxl import load_workbook

from ..config import FIELDS, Config
from ..models import EmployeeRecord, SourceError
from ..validation import build_records

MAX_WAIT_SECONDS = 300


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))  # 1001.0 -> "1001"
    return str(value).strip()


class ExcelSource:
    def __init__(
        self,
        config: Config,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self._sleep = sleep
        self._clock = clock

    def _wait_stable(self, path: Path) -> None:
        """Wait until mtime and size are unchanged for stable_seconds (file being saved)."""
        stable = self.config.stable_seconds
        start = self._clock()
        last, since = None, start
        while True:
            try:
                st = path.stat()
            except OSError as exc:
                raise SourceError(f"File non accessibile: {path} ({exc})") from exc
            sig, now = (st.st_mtime_ns, st.st_size), self._clock()
            if sig != last:
                last, since = sig, now
            if now - since >= stable:
                return
            if now - start > MAX_WAIT_SECONDS:
                raise SourceError(f"Il file è in continua modifica da oltre {MAX_WAIT_SECONDS}s")
            self._sleep(min(1.0, stable))

    def read(self) -> list[EmployeeRecord]:
        path = self.config.excel_path
        if path.name.startswith("~$"):  # Office lock file, never real data
            raise SourceError(f"Il percorso indica un file di lock di Office: {path}")
        if not path.is_file():
            raise SourceError(f"File Excel non trovato: {path}")
        self._wait_stable(path)
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "snapshot.xlsx"
            try:
                shutil.copyfile(path, copy)  # never hold a lock on the original
            except OSError as exc:
                raise SourceError(f"Impossibile copiare il file: {exc}") from exc
            return self._read_copy(copy)

    def _read_copy(self, copy: Path) -> list[EmployeeRecord]:
        cfg = self.config
        try:
            wb = load_workbook(copy, read_only=True, data_only=True)
            try:
                if cfg.sheet and cfg.sheet not in wb.sheetnames:
                    raise SourceError(f"Foglio non trovato: {cfg.sheet}")
                ws = wb[cfg.sheet] if cfg.sheet else wb.worksheets[0]
                rows_iter = ws.iter_rows(values_only=True)
                header = next(rows_iter, None)
                raw_rows = list(enumerate(rows_iter, start=2))
            finally:
                wb.close()
        except SourceError:
            raise
        except Exception as exc:  # openpyxl raises many types on corrupt files
            raise SourceError(f"File Excel corrotto o illeggibile: {exc}") from exc
        if header is None:
            raise SourceError("Il file è vuoto: nessuna riga di dati")
        names = [_text(h).lower() for h in header]
        index: dict[str, int] = {}
        for name in FIELDS:
            wanted = cfg.columns[name].strip().lower()
            if wanted not in names:
                raise SourceError(f"Colonna obbligatoria mancante: {cfg.columns[name]}")
            index[name] = names.index(wanted)
        rows = []
        for number, cells in raw_rows:
            if not any(_text(c) for c in cells):
                continue
            row = {n: _text(cells[i]) if i < len(cells) else "" for n, i in index.items()}
            rows.append((number, row))
        return build_records(rows, cfg.active_values, cfg.inactive_values)
