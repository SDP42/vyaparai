"""Pull text, with page and heading information, out of PDF, DOCX, TXT and Markdown files.

Untrusted input: size and page caps, DOCX read as a zip with a total-size guard (no macros are
ever run), and no file name is used on disk.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from app.core.errors import AppError

MAX_BYTES = 15 * 1024 * 1024
MAX_PAGES = 200
MAX_CHARS = 2_000_000
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentFileError(AppError):
    status_code = 422
    code = "bad_document"


@dataclass(slots=True)
class Block:
    text: str
    page: int | None = None
    heading: str | None = None  # the nearest heading above this block


def kind_of(filename: str, content: bytes) -> str:
    if content[:5] == b"%PDF-":
        return "pdf"
    if content[:2] == b"PK" and filename.lower().endswith(".docx"):
        return "docx"
    if filename.lower().endswith((".txt", ".md", ".csv")):
        return "text"
    raise DocumentFileError("Upload a PDF, DOCX, TXT or Markdown file.")


def _decode(content: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeError:
            continue
    raise DocumentFileError("The text file could not be read.")


def _looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 90 or s.endswith((".", ",", ";")):
        return False
    return s.startswith("#") or s.isupper() or (len(s.split()) <= 8 and s[0].isupper())


def _from_text(text: str, page: int | None = None) -> list[Block]:
    blocks: list[Block] = []
    heading: str | None = None
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        lines = para.splitlines()
        if len(lines) == 1 and _looks_like_heading(lines[0]):
            heading = lines[0].lstrip("# ").strip()
            continue
        if _looks_like_heading(lines[0]) and len(lines) > 1:
            heading = lines[0].lstrip("# ").strip()
            para = "\n".join(lines[1:]).strip()
        blocks.append(Block(re.sub(r"[ \t]+", " ", para), page, heading))
    return blocks


def _docx(content: bytes) -> list[Block]:
    try:
        z = zipfile.ZipFile(io.BytesIO(content))
        info = z.getinfo("word/document.xml")
        if info.file_size > 30 * 1024 * 1024:
            raise DocumentFileError("That document is too large to read.")
        root = ET.fromstring(z.read(info))  # noqa: S314  (size-checked part of a user document)
    except DocumentFileError:
        raise
    except Exception as exc:
        raise DocumentFileError("That DOCX could not be read.") from exc
    blocks: list[Block] = []
    heading: str | None = None
    for p in root.iter(f"{_W}p"):
        text = "".join(t.text or "" for t in p.iter(f"{_W}t")).strip()
        if not text:
            continue
        style = p.find(f"{_W}pPr/{_W}pStyle")
        sval = (style.get(f"{_W}val") if style is not None else "") or ""
        if sval.lower().startswith(("heading", "title")):
            heading = text
            continue
        blocks.append(Block(text, None, heading))
    return blocks


def _pdf(content: bytes) -> list[Block]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise DocumentFileError("That PDF is password protected.")
        blocks: list[Block] = []
        for i, page in enumerate(reader.pages[:MAX_PAGES], 1):
            blocks += _from_text(page.extract_text() or "", i)
    except DocumentFileError:
        raise
    except Exception as exc:
        raise DocumentFileError("That PDF could not be read.") from exc
    return blocks


def extract(filename: str, content: bytes) -> tuple[str, list[Block]]:
    """Returns (kind, blocks). Raises DocumentFileError for unreadable or empty files."""
    if len(content) > MAX_BYTES:
        raise DocumentFileError("The file is larger than 15 MB.")
    kind = kind_of(filename, content)
    blocks = (
        _pdf(content)
        if kind == "pdf"
        else _docx(content)
        if kind == "docx"
        else _from_text(_decode(content))
    )
    if sum(len(b.text) for b in blocks) > MAX_CHARS:
        raise DocumentFileError("That document has too much text to index.")
    if not blocks:
        msg = "No text was found. Scanned PDFs need to be photographed as bills or typed in."
        raise DocumentFileError(msg)
    return kind, blocks
