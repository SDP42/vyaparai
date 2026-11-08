"""Phase 1 ingestion: upload → inspect → map → validate → import, with known-answer fixtures."""

import io
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.services.ingestion.fields import suggest_mapping
from app.services.ingestion.parsing import ParseError, parse_date, parse_number, parse_status

# 5 valid lines across 3 orders + 3 bad rows. Header names mimic a billing-tool export.
# ruff: noqa: E501  (CSV fixtures are clearer on one line each)
GOOD = """Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Status,GST
INV-1,05/10/2026,ATT-5KG,Atta 5kg,Staples,2,295,10,248,C-1,Maharashtra,Pune,Paid,14.75
INV-1,05/10/2026,GHE-1L,Desi Ghee 1L,Dairy,1,645,0,560,C-1,Maharashtra,Pune,Paid,32.25
INV-2,06/10/2026,ATT-5KG,Atta 5kg,Staples,1,"₹1,000",0,248,C-2,Gujarat,Surat,Delivered,0
INV-3,07/10/2026,OIL-5L,Mustard Oil 5L,Staples,3,380,40,330,,,,Cancelled,0
INV-3,07/10/2026,TEA-500,Tea 500g,Beverages,1,240,0,190,,,,Cancelled,0
"""
BAD = """INV-4,not a date,ATT-5KG,Atta 5kg,Staples,1,295,0,248,C-3,,,Paid,0
INV-5,08/10/2026,,Mystery item,Misc,1,100,0,,C-3,,,Paid,0
INV-6,08/10/2026,RIC-5KG,Rice 5kg,Staples,-2,500,0,420,C-3,,,Paid,0
"""
# Net sales (completed only): INV-1 (2*295-10 + 645) + INV-2 (1000) = 1225 + 1000 = 2225.00
EXPECTED_NET = "2225.00"


@pytest.fixture
def ws(client: TestClient, make_user):
    owner = make_user("owner@shop.in", "Owner")
    w = client.post("/api/v1/workspaces", json={"name": "Kulkarni Stores"}, headers=owner).json()
    return owner, w["id"]


def upload(client, headers, ws_id, content: bytes, filename="sales.csv"):
    return client.post(
        f"/api/v1/workspaces/{ws_id}/datasets",
        files={"file": (filename, content, "text/csv")},
        headers=headers,
    )


def full_flow(client, headers, ws_id, content: bytes, filename="sales.csv"):
    r = upload(client, headers, ws_id, content, filename)
    assert r.status_code == 201, r.text
    ds = r.json()
    base = f"/api/v1/workspaces/{ws_id}/datasets/{ds['id']}"
    r = client.put(
        f"{base}/mapping",
        json={"fields": ds["column_mapping"]["fields"], "date_order": "dmy"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    r = client.post(f"{base}/validate", headers=headers)
    assert r.status_code == 200, r.text
    return ds, base, r.json()


def test_upload_inspects_and_suggests_mapping(client: TestClient, ws) -> None:
    h, ws_id = ws
    r = upload(client, h, ws_id, (GOOD + BAD).encode())
    assert r.status_code == 201, r.text
    ds = r.json()
    assert ds["status"] == "uploaded"
    assert ds["row_count"] == 8
    fields = ds["column_mapping"]["fields"]
    assert fields["order_id"] == "Bill No"
    assert fields["order_date"] == "Bill Date"
    assert fields["sku"] == "Item Code"
    assert fields["product_name"] == "Item Name"
    assert fields["quantity"] == "Qty"
    assert fields["unit_price"] == "Rate"
    assert fields["tax_amount"] == "GST"
    cols = {c["name"]: c for c in ds["inspection"]["columns"]}
    assert cols["Qty"]["inferred_type"] == "number"
    assert cols["Bill Date"]["inferred_type"] == "text"  # one unparseable date among 8
    assert len(ds["inspection"]["sample_rows"]) == 8


def test_validation_counts_reconcile(client: TestClient, ws) -> None:
    h, ws_id = ws
    _, _, summary = full_flow(client, h, ws_id, (GOOD + BAD).encode())
    assert summary["rows_total"] == 8
    assert summary["rows_valid"] == 5
    assert summary["rows_invalid"] == 3
    assert summary["rows_valid"] + summary["rows_invalid"] == summary["rows_total"]
    assert summary["errors_by_field"] == {"order_date": 1, "sku": 1, "quantity": 1}
    assert summary["preview"]["orders"] == 3
    assert summary["preview"]["net_sales_completed"] == EXPECTED_NET
    rows = {e["row"] for e in summary["sample_errors"]}
    assert rows == {7, 8, 9}


def test_import_creates_normalised_records(client: TestClient, ws) -> None:
    h, ws_id = ws
    _, base, _ = full_flow(client, h, ws_id, (GOOD + BAD).encode())
    r = client.post(f"{base}/import", headers=h)
    assert r.status_code == 202, r.text
    job = client.get(f"/api/v1/workspaces/{ws_id}/jobs/{r.json()['id']}", headers=h).json()
    assert job["status"] == "succeeded", job
    assert job["rows_accepted"] == 5
    assert job["rows_rejected"] == 3
    assert job["result"]["orders_created"] == 3
    assert job["result"]["products_created"] == 4
    assert job["result"]["customers_created"] == 2

    s = client.get(f"/api/v1/workspaces/{ws_id}/data-summary", headers=h).json()
    assert s["orders"] == 3
    assert s["order_items"] == 5
    assert s["products"] == 4
    assert Decimal(s["net_sales_completed"]) == Decimal(EXPECTED_NET)
    assert s["date_from"] == "2026-10-05"
    assert s["date_to"] == "2026-10-07"

    assert client.get(base, headers=h).json()["status"] == "imported"
    again = client.post(f"{base}/import", headers=h)
    assert again.status_code == 409


def test_reimport_skips_existing_orders(client: TestClient, ws) -> None:
    h, ws_id = ws
    _, base, _ = full_flow(client, h, ws_id, GOOD.encode())
    client.post(f"{base}/import", headers=h)
    newer = GOOD + "INV-7,09/10/2026,ATT-5KG,Atta 5kg,Staples,1,295,0,248,C-1,,,Paid,0\n"
    _, base2, _ = full_flow(client, h, ws_id, newer.encode(), "sales_v2.csv")
    job = client.post(f"{base2}/import", headers=h).json()
    job = client.get(f"/api/v1/workspaces/{ws_id}/jobs/{job['id']}", headers=h).json()
    assert job["result"]["orders_created"] == 1
    assert job["result"]["duplicate_orders_skipped"] == 3
    s = client.get(f"/api/v1/workspaces/{ws_id}/data-summary", headers=h).json()
    assert s["orders"] == 4
    assert s["products"] == 4  # no duplicate products


def test_error_csv_download(client: TestClient, ws) -> None:
    h, ws_id = ws
    _, base, _ = full_flow(client, h, ws_id, (GOOD + BAD).encode())
    r = client.get(f"{base}/errors.csv", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0] == "row,field,column,message,value"
    assert len(lines) == 4


def test_duplicate_file_rejected(client: TestClient, ws) -> None:
    h, ws_id = ws
    first = upload(client, h, ws_id, GOOD.encode()).json()
    r = upload(client, h, ws_id, GOOD.encode(), "copy.csv")
    assert r.status_code == 409
    assert r.json()["error"]["details"]["dataset_id"] == first["id"]


@pytest.mark.parametrize(
    ("name", "content", "code"),
    [
        ("sales.pdf", b"%PDF-1.4", 415),
        ("sales.xlsx", b"not really a zip", 415),
        ("sales.csv", b"PK\x03\x04binary", 415),
        ("sales.csv", b"Bill No,Bill Date\n", 415),
    ],
)
def test_bad_files_rejected(client: TestClient, ws, name, content, code) -> None:
    h, ws_id = ws
    r = upload(client, h, ws_id, content, name)
    assert r.status_code == code, r.text
    assert r.json()["error"]["code"] == "unsupported_file"


def test_mapping_requires_all_required_fields(client: TestClient, ws) -> None:
    h, ws_id = ws
    ds = upload(client, h, ws_id, GOOD.encode()).json()
    fields = dict(ds["column_mapping"]["fields"])
    fields.pop("unit_price")
    r = client.put(
        f"/api/v1/workspaces/{ws_id}/datasets/{ds['id']}/mapping",
        json={"fields": fields},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_mapping"
    assert "Unit price" in r.json()["error"]["message"]


def test_validate_before_mapping_is_rejected(client: TestClient, ws) -> None:
    h, ws_id = ws
    ds = upload(client, h, ws_id, GOOD.encode()).json()
    r = client.post(f"/api/v1/workspaces/{ws_id}/datasets/{ds['id']}/validate", headers=h)
    assert r.status_code == 409
    r = client.post(f"/api/v1/workspaces/{ws_id}/datasets/{ds['id']}/import", headers=h)
    assert r.status_code == 409


def test_xlsx_upload_and_import(client: TestClient, ws) -> None:
    h, ws_id = ws
    wb = Workbook()
    sheet = wb.active
    sheet.append(["Order ID", "Order Date", "SKU", "Product Name", "Quantity", "Unit Price"])
    sheet.append(["X-1", datetime(2026, 10, 1), "A1", "Item A", 2, 100.0])
    sheet.append(["X-2", datetime(2026, 10, 2, 14, 30), "B1", "Item B", 1, 50.5])
    buf = io.BytesIO()
    wb.save(buf)
    _, base, summary = full_flow(client, h, ws_id, buf.getvalue(), "export.xlsx")
    assert summary["rows_valid"] == 2
    assert summary["preview"]["net_sales_completed"] == "250.50"
    job = client.post(f"{base}/import", headers=h).json()
    job = client.get(f"/api/v1/workspaces/{ws_id}/jobs/{job['id']}", headers=h).json()
    assert job["status"] == "succeeded"


def test_viewer_cannot_upload_and_other_tenant_cannot_see(
    client: TestClient, ws, make_user
) -> None:
    h, ws_id = ws
    viewer = make_user("viewer@shop.in")
    client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "viewer@shop.in", "role": "viewer"},
        headers=h,
    )
    assert upload(client, viewer, ws_id, GOOD.encode()).status_code == 403

    ds = upload(client, h, ws_id, GOOD.encode()).json()
    outsider = make_user("outsider@else.in")
    r = client.get(f"/api/v1/workspaces/{ws_id}/datasets/{ds['id']}", headers=outsider)
    assert r.status_code == 404


def test_audit_trail_for_ingestion(client: TestClient, ws) -> None:
    h, ws_id = ws
    _, base, _ = full_flow(client, h, ws_id, GOOD.encode())
    client.post(f"{base}/import", headers=h)
    actions = {
        e["action"]
        for e in client.get(f"/api/v1/workspaces/{ws_id}/audit-logs?limit=200", headers=h).json()[
            "items"
        ]
    }
    assert {
        "dataset.uploaded",
        "dataset.mapped",
        "dataset.import_started",
        "dataset.imported",
    } <= actions


# ---------- parsers ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("₹1,23,456.50", "123456.50"),
        ("1,000", "1000"),
        ("(12)", "-12"),
        (" 42 ", "42"),
        (7, "7"),
        ("Rs. 99", "99"),
    ],
)
def test_parse_number(raw, expected) -> None:
    assert parse_number(raw) == Decimal(expected)


def test_parse_number_rejects_text() -> None:
    with pytest.raises(ParseError):
        parse_number("abc")


def test_parse_date_day_first_by_default() -> None:
    assert parse_date("05/03/2026") == datetime(2026, 3, 5, tzinfo=UTC)
    assert parse_date("05/03/2026", "mdy") == datetime(2026, 5, 3, tzinfo=UTC)
    assert parse_date("2026-03-05") == datetime(2026, 3, 5, tzinfo=UTC)
    assert parse_date("05-Mar-2026") == datetime(2026, 3, 5, tzinfo=UTC)
    assert parse_date("05/03/2026 14:30") == datetime(2026, 3, 5, 14, 30, tzinfo=UTC)


def test_parse_status() -> None:
    assert parse_status("Paid").value == "completed"
    assert parse_status("").value == "completed"
    assert parse_status("Canceled").value == "cancelled"
    with pytest.raises(ParseError):
        parse_status("teleported")


def test_suggest_mapping_prefers_exact_matches() -> None:
    m = suggest_mapping(
        [
            "InvoiceNo",
            "StockCode",
            "Description",
            "Quantity",
            "InvoiceDate",
            "UnitPrice",
            "CustomerID",
        ]
    )
    assert m["sku"] == "StockCode"
    assert m["product_name"] == "Description"
    assert m["order_date"] == "InvoiceDate"
    assert m["unit_price"] == "UnitPrice"
    assert m["customer_id"] == "CustomerID"
