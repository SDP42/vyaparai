"""Safe reading of uploaded CSV / XLSX files into header + row iterators."""

import csv
import io
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.errors import AppError

ALLOWED_TYPES = ("csv", "xlsx")
_XLSX_MAGIC = b"PK\x03\x04"


class UnsupportedFileError(AppError):
    status_code = 415
    code = "unsupported_file"


class FileTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


def detect_type(filename: str, head: bytes) -> str:
    """Decide the file type from the extension and confirm it with the file signature."""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_TYPES:
        raise UnsupportedFileError("Only .csv and .xlsx files are supported")
    if ext == "xlsx" and not head.startswith(_XLSX_MAGIC):
        raise UnsupportedFileError("This .xlsx file is not a valid Excel workbook")
    if ext == "csv" and (head.startswith(_XLSX_MAGIC) or b"\x00" in head[:4096]):
        raise UnsupportedFileError("This .csv file looks binary, not text")
    return ext


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise UnsupportedFileError("Could not decode the CSV file (try saving it as UTF-8)")


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, datetime | date):
        return v
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def read_table(path: Path, file_type: str) -> tuple[list[str], Iterator[list[Any]]]:
    """Return (headers, rows). Rows are lists aligned to headers; empty rows are skipped."""
    if file_type == "csv":
        text = _decode(path.read_bytes())
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(io.StringIO(text), dialect)
        try:
            headers = [h.strip() for h in next(reader)]
        except StopIteration as exc:
            raise UnsupportedFileError("The file is empty") from exc

        def csv_rows() -> Iterator[list[Any]]:
            for row in reader:
                if any(c.strip() for c in row):
                    yield [c.strip() for c in row] + [""] * (len(headers) - len(row))

        return headers, csv_rows()

    from openpyxl import load_workbook

    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # corrupt or password-protected workbooks
        raise UnsupportedFileError("Could not open the Excel workbook") from exc
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    try:
        first = next(it)
    except StopIteration as exc:
        raise UnsupportedFileError("The first worksheet is empty") from exc
    headers = [str(h).strip() if h is not None else "" for h in first]

    def xlsx_rows() -> Iterator[list[Any]]:
        for row in it:
            cells = [_cell(v) for v in row]
            if any(c != "" for c in cells):
                yield cells + [""] * (len(headers) - len(cells))
        wb.close()

    return headers, xlsx_rows()
