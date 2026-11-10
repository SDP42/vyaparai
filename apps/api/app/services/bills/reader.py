"""Get text lines out of a bill file: a PDF with text, a scanned PDF, or a photo.

Order of attempts (first that works wins):
1. PDF text layer (pypdf): exact, no OCR needed.
2. RapidOCR (Apache-2.0, PaddleOCR models on ONNX, CPU) when the package is installed.
3. Tesseract (Apache-2.0) when its program is installed.
Untrusted files: size and pixel caps, no file names reach a command, subprocess has a timeout.
"""

import io
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, ImageOps

from app.core.errors import AppError

logger = logging.getLogger(__name__)
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_PDF_PAGES = 5
OCR_TIMEOUT = 40


class BillFileError(AppError):
    status_code = 422
    code = "bad_bill_file"


@dataclass(slots=True)
class ReadResult:
    lines: list[str]
    engine: str
    pages: int = 1
    warnings: list[str] = field(default_factory=list)


def available_engines() -> list[str]:
    out = []
    try:
        import rapidocr_onnxruntime  # noqa: F401

        out.append("rapidocr")
    except Exception:
        logger.info("RapidOCR is not available")
    if shutil.which("tesseract"):
        out.append("tesseract")
    return out


def kind_of(content: bytes) -> str:
    if content[:5] == b"%PDF-":
        return "pdf"
    if (
        content[:3] == b"\xff\xd8\xff"
        or content[:8] == b"\x89PNG\r\n\x1a\n"
        or content[:4] == b"RIFF"
    ):
        return "image"
    raise BillFileError("Upload a photo (JPG, PNG, WebP) or a PDF of the bill.")


def _prepare(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    img = ImageOps.grayscale(img)
    w, h = img.size
    if max(w, h) < 1600:  # small photos OCR badly; enlarge
        scale = 1600 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return ImageOps.autocontrast(img)


def _open_image(data: bytes) -> Image.Image:
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise BillFileError("That image could not be read.") from exc
    return img


def _group_boxes(items: list[tuple[float, float, float, str]]) -> list[str]:
    """(x, y_center, height, text) pieces -> text lines, left to right, top to bottom."""
    items = sorted(items, key=lambda t: t[1])
    rows: list[list[tuple[float, float, float, str]]] = []
    for it in items:
        if rows and abs(it[1] - rows[-1][-1][1]) <= max(it[2], rows[-1][-1][2]) * 0.6:
            rows[-1].append(it)
        else:
            rows.append([it])
    return [" ".join(p[3] for p in sorted(r, key=lambda t: t[0])) for r in rows]


def _rapidocr(img: Image.Image) -> list[str]:
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    engine: Any = _rapidocr_engine()
    if engine is None:
        engine = RapidOCR()
    result, _ = engine(np.array(img.convert("RGB")))
    if not result:
        return []
    pieces = []
    for box, text, _score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        pieces.append((min(xs), (min(ys) + max(ys)) / 2, max(ys) - min(ys), str(text)))
    return _group_boxes(pieces)


_ENGINE: Any = None


def _rapidocr_engine() -> Any:
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR

        _ENGINE = RapidOCR()
    return _ENGINE


def _tesseract(img: Image.Image) -> list[str]:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    try:
        proc = subprocess.run(
            ["tesseract", "stdin", "stdout", "--psm", "6", "-c", "preserve_interword_spaces=1"],  # noqa: S607
            input=buf.getvalue(), capture_output=True, timeout=OCR_TIMEOUT, check=False,
        )  # fmt: skip
    except subprocess.TimeoutExpired as exc:
        raise BillFileError(
            "Reading the photo took too long. Try a smaller or clearer one."
        ) from exc
    if proc.returncode != 0:
        raise BillFileError("The text reader failed on that image.")
    return [ln for ln in proc.stdout.decode("utf-8", "replace").splitlines() if ln.strip()]


def _ocr(img: Image.Image) -> tuple[list[str], str]:
    engines = available_engines()
    if not engines:
        raise BillFileError(
            "No text reader is installed on the server. Install Tesseract or the rapidocr-onnxruntime "
            "package, or upload a PDF that contains text."
        )
    img = _prepare(img)
    if "rapidocr" in engines:
        try:
            return _rapidocr(img), "rapidocr"
        except Exception:
            if "tesseract" not in engines:
                raise BillFileError("The text reader failed on that image.") from None
    return _tesseract(img), "tesseract"


def _pdf_text(content: bytes) -> tuple[list[str], int]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise BillFileError("That PDF is password protected.")
        n = len(reader.pages)
        lines: list[str] = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            lines += (page.extract_text() or "").splitlines()
    except BillFileError:
        raise
    except Exception as exc:
        raise BillFileError("That PDF could not be read.") from exc
    return [ln for ln in lines if ln.strip()], n


def _pdf_images(content: bytes) -> list[Image.Image]:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise BillFileError(
            "This PDF is a scan and the server cannot turn it into images. Upload a photo instead."
        ) from exc
    pdf = pdfium.PdfDocument(content)
    return [pdf[i].render(scale=2.5).to_pil() for i in range(min(len(pdf), MAX_PDF_PAGES))]


def read_bill(content: bytes) -> ReadResult:
    if len(content) > MAX_BYTES:
        raise BillFileError("The file is larger than 10 MB.")
    kind = kind_of(content)
    if kind == "pdf":
        lines, pages = _pdf_text(content)
        if sum(len(x) for x in lines) >= 80:
            return ReadResult(lines, "pdf-text", pages)
        out: list[str] = []
        engine = ""
        for im in _pdf_images(content):
            got, engine = _ocr(im)
            out += got
        return ReadResult(out, engine, pages, ["Scanned PDF read with OCR."])
    lines, engine = _ocr(_open_image(content))
    warn = [] if lines else ["No text was found in the image."]
    return ReadResult(lines, engine, 1, warn)
