"""Reports: a saved snapshot, rendered as PDF and CSV, with numbers from the metric layer."""

import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.services.reports import render
from tests.test_forecast_api import shop_csv
from tests.test_intelligence_api import make_shop
from tests.test_team import _join


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "rep@shop.in", shop_csv(84))


def _create(client, shop, **body):
    h, ws = shop
    return client.post(f"/api/v1/workspaces/{ws}/reports", json=body, headers=h)


def test_rupee_formatting_in_the_pdf_uses_indian_grouping() -> None:
    assert render.rs(1234567) == "₹12,34,567"
    assert render.rs(999) == "₹999"
    assert render.rs(-52300.6) == "-₹52,301"
    assert render.rs(None) == "-"


def test_a_report_is_saved_with_the_dashboard_numbers(client: TestClient, shop) -> None:
    h, ws = shop
    r = _create(client, shop, date_from="2026-09-26", date_to="2026-10-25")
    assert r.status_code == 201, r.text
    rep = r.json()["content"]
    ov = client.get(
        f"/api/v1/workspaces/{ws}/analytics/overview?from=2026-09-26&to=2026-10-25", headers=h
    ).json()
    net = next(k for k in ov["headline"] if k["key"] == "net_sales")
    got = next(k for k in rep["kpis"] if k["key"] == "net_sales")
    assert got["value"] == float(net["value"])
    assert rep["period"]["from"] == "2026-09-26"
    assert rep["limits"]
    assert rep["trend"]


def test_the_pdf_is_a_real_document_with_the_shop_and_numbers(client: TestClient, shop) -> None:
    h, ws = shop
    rid = _create(client, shop).json()["id"]
    pdf = client.get(f"/api/v1/workspaces/{ws}/reports/{rid}/pdf", headers=h)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Shop" in text
    assert "Net sales" in text.title() or "NET SALES" in text
    assert "₹" in text
    assert "Notes and limits" in text


def test_the_csv_has_sections_and_matches_the_report(client: TestClient, shop) -> None:
    h, ws = shop
    r = _create(client, shop).json()
    csv_text = client.get(f"/api/v1/workspaces/{ws}/reports/{r['id']}/csv", headers=h).text
    lines = csv_text.splitlines()
    assert lines[0] == "Section,Item,Value,Previous,Change %"
    assert any(ln.startswith("Measures,Net sales,") for ln in lines)
    assert any(ln.startswith("Top products,") for ln in lines)


def test_a_saved_report_is_frozen_while_the_data_moves_on(client: TestClient, shop) -> None:
    h, ws = shop
    r = _create(client, shop).json()
    before = client.get(f"/api/v1/workspaces/{ws}/reports/{r['id']}", headers=h).json()["content"][
        "kpis"
    ]
    client.post(
        f"/api/v1/workspaces/{ws}/udhaar/entries",
        json={"party": "X", "kind": "credit", "amount": "10"},
        headers=h,
    )
    after = client.get(f"/api/v1/workspaces/{ws}/reports/{r['id']}", headers=h).json()["content"][
        "kpis"
    ]
    assert before == after
    assert len(client.get(f"/api/v1/workspaces/{ws}/reports", headers=h).json()) == 1


def test_empty_workspace_is_refused_clearly(client: TestClient, make_user) -> None:
    h = make_user("e@shop.in")
    ws = client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=h).json()["id"]
    r = client.post(f"/api/v1/workspaces/{ws}/reports", json={}, headers=h)
    assert r.status_code == 400
    assert "No sales" in r.json()["error"]["message"]


def test_permissions_and_delete(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    rid = _create(client, shop).json()["id"]
    viewer = make_user("v@shop.in")
    _join(client, ws, h, viewer, "viewer")
    base = f"/api/v1/workspaces/{ws}/reports"
    assert client.get(f"{base}/{rid}/pdf", headers=viewer).status_code == 200
    assert client.post(base, json={}, headers=viewer).status_code == 403
    assert client.delete(f"{base}/{rid}", headers=viewer).status_code == 403
    stranger = make_user("s@s.in")
    assert client.get(f"{base}/{rid}", headers=stranger).status_code == 404
    assert client.delete(f"{base}/{rid}", headers=h).status_code == 204
    assert client.get(f"{base}/{rid}", headers=h).status_code == 404


def test_a_report_period_is_trimmed_to_the_days_with_data(client: TestClient, shop) -> None:
    r = _create(client, shop, date_from="2026-10-10", date_to="2026-12-31").json()
    assert r["content"]["period"]["to"] == "2026-10-25"


def test_the_report_carries_and_prints_metric_definitions(client: TestClient, shop) -> None:
    h, ws = shop
    r = _create(client, shop).json()
    defs = r["content"]["definitions"]
    assert any(d["label"] == "Net sales" and d["definition"] for d in defs)
    pdf = client.get(f"/api/v1/workspaces/{ws}/reports/{r['id']}/pdf", headers=h)
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "How the measures are defined" in text
