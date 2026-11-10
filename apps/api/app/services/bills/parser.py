"""Turn the text of a supplier bill into a supplier, date, bill number and item lines.

Works on plain text lines, whatever produced them (a PDF text layer or OCR), so it is tested
without any image. Each item line carries a confidence: high when quantity x rate matches the
printed amount, low when a number had to be guessed. Nothing here is saved; a person confirms.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

D = Decimal

_NUM = re.compile(r"^[₹]?\(?-?\d[\d,]*(?:\.\d+)?\)?$")
_PCT = re.compile(r"^\d+(?:\.\d+)?%$")
_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
_UNITS = {
    "pcs", "pc", "nos", "no", "kg", "kgs", "g", "gm", "gms", "ltr", "ltrs", "l", "ml", "box",
    "boxes", "pkt", "pkts", "packet", "packets", "dozen", "doz", "bag", "bags", "set", "pair",
    "unit", "units", "btl", "bottle", "carton", "ctn", "case", "itr", "1tr",
}  # fmt: skip
_SKIP = re.compile(
    r"\b(sub\s*total|total|grand|cgst|sgst|igst|gst|tax|round\s*off|discount|freight|balance|"
    r"amount\s+in\s+words|bank|ifsc|a/c|account|terms|signature|declaration|e\.?\s*&\s*o\.?\s*e|"
    r"received|thank|page|hsn\s*/|particulars|description|qty|quantity|rate|amount)\b",
    re.I,
)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}  # fmt: skip
_DATE_NUM = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_TXT = re.compile(r"\b(\d{1,2})[\s\-]([A-Za-z]{3})[a-z]*[\s\-,]+(\d{2,4})\b")
_BILL_NO = re.compile(
    r"\b(?:invoice|inv|bill|voucher|challan)[ \t]*(?:no\.?|number|#|num)?[ \t]*[:.\-]?[ \t]*([A-Za-z0-9][A-Za-z0-9/\-]{1,24})",
    re.I,
)
_TOTAL = re.compile(
    r"(grand\s*total|net\s*(?:amount|payable)|amount\s*payable|invoice\s*total|total\s*amount|total)",
    re.I,
)
_HEADER_WORDS = re.compile(
    r"invoice|tax|bill|gstin|original|duplicate|cash|memo|date|phone|mob|email|address|"
    r"customer|ship|buyer|consignee|estimate|quotation|proforma",
    re.I,
)


@dataclass(slots=True)
class ParsedLine:
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    unit: str | None = None
    confidence: str = "high"  # high | medium | low
    raw: str = ""


@dataclass(slots=True)
class ParsedBill:
    supplier: str | None = None
    gstin: str | None = None
    bill_no: str | None = None
    bill_date: date | None = None
    total: Decimal | None = None
    lines: list[ParsedLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def to_decimal(tok: str) -> Decimal | None:
    t = tok.replace("₹", "").replace(",", "").strip("()")
    neg = tok.startswith("(") or t.startswith("-")
    try:
        v = D(t.lstrip("-"))
    except InvalidOperation:
        return None
    return -v if neg else v


def _year(y: int) -> int:
    return y + 2000 if y < 100 else y


def parse_date(text: str) -> date | None:
    """First plausible date in the text. Day-first, as Indian bills are."""
    for m in _DATE_ISO.finditer(text):
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            continue
    for m in _DATE_NUM.finditer(text):
        try:
            return date(_year(int(m[3])), int(m[2]), int(m[1]))
        except ValueError:
            continue
    for m in _DATE_TXT.finditer(text):
        mon = _MONTHS.get(m[2].lower())
        if mon:
            try:
                return date(_year(int(m[3])), mon, int(m[1]))
            except ValueError:
                continue
    return None


def _close(a: Decimal, b: Decimal, tol: Decimal = D("0.03")) -> bool:
    if b == 0:
        return a == 0
    return abs(a - b) / abs(b) <= tol or abs(a - b) <= D("1.0")


def _parse_item(line: str) -> ParsedLine | None:
    toks = line.split()
    nums: list[tuple[int, Decimal]] = []
    for i, t in enumerate(toks):
        v = to_decimal(t) if _NUM.match(t) and not _PCT.match(t) else None
        if v is not None:
            nums.append((i, v))
    if len(nums) < 2:
        return None
    # leave the serial number out of the description: "1 Tata Salt ..." / "1. Tata Salt ..."
    start = 1 if toks and re.fullmatch(r"\d{1,3}\.?", toks[0]) and len(toks) > 2 else 0
    nums = [(i, v) for i, v in nums if i >= start]
    if len(nums) < 2:
        return None
    first_num = nums[0][0]
    tail = nums[-5:]
    amount = tail[-1][1]
    best: tuple[int, Decimal, Decimal, str] | None = None  # (rank, qty, rate, confidence)
    for a in range(len(tail) - 1):
        for b in range(a + 1, len(tail) - 1):
            q, r = tail[a][1], tail[b][1]
            if q > 0 and r > 0 and _close(q * r, amount):
                # prefer a small quantity and the closest pair to the amount
                rank = b - a
                if best is None or (q < best[1] and rank <= best[0]):
                    best = (rank, q, r, "high")
    if best is None:
        prev = tail[-2][1]
        if len(tail) >= 2 and prev > 0 and amount > 0:
            q = prev if prev == prev.to_integral_value() and prev <= 10000 else D(1)
            best = (0, q, (amount / q).quantize(D("0.01")), "low")
        else:
            return None
    _, qty, rate, conf = best
    unit = next((toks[i + 1].lower().strip(".,") for i, v in nums if v == qty and i + 1 < len(toks)
                 and toks[i + 1].lower().strip(".,") in _UNITS), None)  # fmt: skip
    # description: words before the first number that is not a serial or HSN, plus words
    # between serial and numbers
    desc_toks = toks[start:first_num]
    while desc_toks and (desc_toks[-1].lower().strip(".,") in _UNITS or _PCT.match(desc_toks[-1])):
        desc_toks.pop()
    desc = " ".join(desc_toks).strip(" -:|.,")
    if not re.search(r"[A-Za-zऀ-ॿ]{2,}", desc):
        return None
    if conf == "high" and qty == D(1) and rate == amount:
        conf = "medium"
    if unit in {"itr", "1tr"}:  # OCR reads the l of ltr as I or 1
        unit = "ltr"
    return ParsedLine(desc[:255], qty, rate, amount, unit, conf, line.strip())


def parse(lines: list[str]) -> ParsedBill:
    out = ParsedBill()
    cleaned = [re.sub(r"[|_]+", " ", ln).strip() for ln in lines]
    cleaned = [re.sub(r"\s{2,}", " ", ln) for ln in cleaned if ln.strip()]
    text = "\n".join(cleaned)
    # OCR often glues words to numbers ("GrandTotal13,061.58"): split them for item and total rules,
    # but keep the raw text for the GSTIN, whose letters and digits are meant to touch.
    spaced = [re.sub(r"(?<=[A-Za-z])(?=\d)", " ", ln) for ln in cleaned]

    m = _GSTIN.search(text.upper())
    out.gstin = m.group(0) if m else None
    dm = re.search(r"(?:date|dated|dt)\s*[:.\-]?\s*(.{0,24})", text, re.I)
    out.bill_date = (parse_date(dm.group(1)) if dm else None) or parse_date(text)
    for bm in _BILL_NO.finditer(text):
        cand = bm.group(1).strip("-/")
        if re.search(r"\d", cand) and not _GSTIN.fullmatch(cand.upper()):
            out.bill_no = cand
            break
    for ln in cleaned[:8]:
        if (
            len(re.findall(r"[A-Za-z]", ln)) >= 3
            and not _HEADER_WORDS.search(ln)
            and not _GSTIN.search(ln.upper())
        ):
            out.supplier = ln[:120]
            break

    totals: list[Decimal] = []
    for ln in spaced:
        if _TOTAL.search(ln) and not re.search(r"sub\s*total|cgst|sgst|igst", ln, re.I):
            vals = [v for t in ln.split() if _NUM.match(t) and (v := to_decimal(t)) and v > 0]
            if vals:
                totals.append(vals[-1])
    out.total = max(totals) if totals else None

    for ln in spaced:
        if _SKIP.search(ln) and not re.search(r"\d+\s*(?:pcs|kg|nos|ltr|box)\b", ln, re.I):
            continue
        item = _parse_item(ln)
        if item:
            out.lines.append(item)

    if not out.lines:
        out.warnings.append(
            "No item lines were recognised. Check the photo, or add the lines by hand."
        )
    if out.bill_date is None:
        out.warnings.append("No bill date found. Set it before confirming.")
    if out.total is not None and out.lines:
        s = sum((x.amount for x in out.lines), D(0))
        if not _close(s, out.total, D("0.05")):
            out.warnings.append(
                f"The lines add up to {s:,.2f} but the bill total is {out.total:,.2f}. "
                "A line may be missing or misread."
            )
    if any(x.confidence == "low" for x in out.lines):
        out.warnings.append("Some lines had a guessed rate or quantity. Check the marked ones.")
    return out
