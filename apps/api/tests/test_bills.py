# ruff: noqa: E501  (long literals are clearer on one line)
"""Purchase bills: reading text, reading images, and the draft -> confirm -> price history flow."""

import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.services.bills import parser, reader
from tests.test_intelligence_api import make_shop

BILL = """SHREE GANESH TRADERS
GSTIN: 27ABCDE1234F1Z5
TAX INVOICE
Invoice No: GT/2026/0412        Date: 05/11/2026
Sr Description HSN Qty Rate Amount
1 Tata Salt 1kg 2501 24 pcs 22.00 528.00
2. Aashirvaad Atta 5kg 1101 10 Nos 245.50 2,455.00
3 Fortune Sunflower Oil 1L 1512 20 ltr 138.00 2,760.00
Sub Total 5,743.00
Grand Total 5,743.00"""


def _png(text: str) -> bytes:
    lines = text.splitlines()
    img = Image.new("RGB", (1100, 60 + 40 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=26)
    for i, ln in enumerate(lines):
        d.text((30, 30 + 40 * i), ln, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _pdf(text: str) -> bytes:
    """A one-page PDF with a real text layer (hand-built, no library needed)."""
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")  # noqa: E731
    body = (
        "BT /F1 11 Tf 40 780 Td 14 TL "
        + " ".join(f"({esc(ln)}) Tj T*" for ln in text.splitlines())
        + " ET"
    )
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode()
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF".encode()
    return out


# ------------------------------------------------------------------ parser


def test_parser_reads_a_clean_bill() -> None:
    b = parser.parse(BILL.splitlines())
    assert b.supplier == "SHREE GANESH TRADERS"
    assert b.gstin == "27ABCDE1234F1Z5"
    assert b.bill_no == "GT/2026/0412"
    assert str(b.bill_date) == "2026-11-05"
    assert b.total == Decimal("5743.00")
    assert [(x.description, x.quantity, x.unit_price) for x in b.lines] == [
        ("Tata Salt 1kg", 24, Decimal("22.00")),
        ("Aashirvaad Atta 5kg", 10, Decimal("245.50")),
        ("Fortune Sunflower Oil 1L", 20, Decimal("138.00")),
    ]
    assert not b.warnings


def test_parser_survives_glued_ocr_text_and_warns_on_a_missing_line() -> None:
    lines = [
        "RAJU KIRANA STORE", "InvoiceNo:R-77 Date:12-10-26",
        "1 Maggi Noodles 12 pcs 14.00 168.00", "2 Surf Excel 1kg 3 210.00 630.00",
        "GrandTotal1,500.00",
    ]  # fmt: skip
    b = parser.parse(lines)
    assert b.bill_no == "R-77"
    assert str(b.bill_date) == "2026-10-12"
    assert b.total == Decimal("1500.00")
    assert len(b.lines) == 2
    assert any("add up" in w for w in b.warnings)


def test_parser_guesses_flag_low_confidence() -> None:
    b = parser.parse(["Some Shop", "Date: 01/01/2026", "Loose Sugar 5 340.00"])
    assert b.lines
    assert b.lines[0].confidence in {"low", "medium"}


def test_parser_never_crashes_on_noise() -> None:
    for t in [[], [""], ["12 34"], ["Total"], ["1 2 3 4 5 6 7"], ["₹ ₹ ₹"], ["a" * 500, "9" * 40]]:
        parser.parse(t)


def test_dates_are_day_first() -> None:
    assert str(parser.parse_date("03/04/2026")) == "2026-04-03"
    assert str(parser.parse_date("5 Nov 2026")) == "2026-11-05"
    assert parser.parse_date("31/02/2026") is None


# ------------------------------------------------------------------ reader


def test_reader_rejects_unknown_and_oversized_files() -> None:
    with pytest.raises(reader.BillFileError):
        reader.read_bill(b"hello world")
    with pytest.raises(reader.BillFileError):
        reader.read_bill(b"%PDF-" + b"0" * (reader.MAX_BYTES + 1))


def test_reader_gets_text_out_of_a_pdf() -> None:
    r = reader.read_bill(_pdf(BILL))
    assert r.engine == "pdf-text"
    assert parser.parse(r.lines).total == Decimal("5743.00")


@pytest.mark.skipif(not reader.available_engines(), reason="no OCR engine installed")
def test_reader_ocrs_a_photo() -> None:
    r = reader.read_bill(_png(BILL))
    b = parser.parse(r.lines)
    assert len(b.lines) == 3
    assert {x.quantity for x in b.lines} == {24, 10, 20}


# ------------------------------------------------------------------ API

SALES = (
    "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status\n"
    "A1,01/10/2026,SKU-1,Tata Salt 1kg,Grocery,5,28,0,20,C1,MH,Pune,Store,Paid\n"
    "A2,02/10/2026,SKU-2,Aashirvaad Atta 5kg,Grocery,3,260,0,230,C2,MH,Pune,Store,Paid\n"
)  # fmt: skip


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "bill@shop.in", SALES)


def _upload(client, h, ws, content: bytes):
    return client.post(
        f"/api/v1/workspaces/{ws}/bills",
        files={"file": ("bill.pdf", content, "application/pdf")},
        headers=h,
    )


def test_upload_matches_products_and_stays_a_draft(client: TestClient, shop) -> None:
    h, ws = shop
    r = _upload(client, h, ws, _pdf(BILL))
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "draft"
    assert b["supplier"] == "SHREE GANESH TRADERS"
    matched = {x["description"]: x["product_id"] is not None for x in b["lines"]}
    assert matched["Tata Salt 1kg"]
    assert matched["Aashirvaad Atta 5kg"]
    assert not matched["Fortune Sunflower Oil 1L"]
    assert _upload(client, h, ws, _pdf(BILL)).status_code == 409  # same file twice


def test_confirm_sets_cost_and_tracks_price_moves(client: TestClient, shop) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/bills"
    first = _upload(client, h, ws, _pdf(BILL)).json()
    done = client.post(f"{base}/{first['id']}/confirm", headers=h)
    assert done.status_code == 200
    assert client.post(f"{base}/{first['id']}/confirm", headers=h).status_code == 409
    assert client.put(f"{base}/{first['id']}", json={"supplier": "X"}, headers=h).status_code == 409

    later = (
        BILL.replace("05/11/2026", "20/11/2026")
        .replace("22.00", "25.00")
        .replace("528.00", "600.00")
    )
    later = later.replace("GT/2026/0412", "GT/2026/0500")
    second = _upload(client, h, ws, _pdf(later)).json()
    res = client.post(f"{base}/{second['id']}/confirm", headers=h).json()
    salt = next(c for c in res["changes"] if "Salt" in c["description"])
    assert salt["change_pct"] == "13.6"

    moves = client.get(f"{base}/prices/moves", headers=h).json()
    assert moves[0]["name"] == "Tata Salt 1kg"
    assert moves[0]["change_pct"] == 13.6
    alerts = client.get(f"/api/v1/workspaces/{ws}/alerts", headers=h).json()
    hit = [a for a in alerts["items"] if a["rule"] == "supplier_price_up"]
    assert hit
    assert hit[0]["severity"] == "medium"


def test_edit_then_confirm_requires_a_date_and_valid_products(client: TestClient, shop) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/bills"
    b = _upload(client, h, ws, _pdf("Some Shop\n1 Tata Salt 1kg 10 20.00 200.00")).json()
    assert b["bill_date"] is None
    assert client.post(f"{base}/{b['id']}/confirm", headers=h).status_code == 400
    bad = client.put(
        f"{base}/{b['id']}",
        json={"lines": [{"description": "X", "quantity": 1, "unit_price": 5,
                         "product_id": "00000000-0000-0000-0000-000000000001"}]},
        headers=h,
    )  # fmt: skip
    assert bad.status_code == 400
    ok = client.put(f"{base}/{b['id']}", json={"bill_date": "2026-10-10"}, headers=h)
    assert ok.status_code == 200
    assert client.post(f"{base}/{b['id']}/confirm", headers=h).status_code == 200


def test_drafts_can_be_discarded_and_others_cannot_see_them(
    client: TestClient, shop, make_user
) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/bills"
    b = _upload(client, h, ws, _pdf(BILL)).json()
    stranger = make_user("s@s.in")
    assert client.get(f"{base}/{b['id']}", headers=stranger).status_code == 404
    assert client.delete(f"{base}/{b['id']}", headers=h).status_code == 204
    assert client.get(f"{base}/{b['id']}", headers=h).status_code == 404
