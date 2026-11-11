"""Cost and margin are hidden from personas without the margin capability."""

from fastapi.testclient import TestClient

from app.api.masking import scrub
from tests.test_forecast_api import shop_csv
from tests.test_intelligence_api import make_shop


def test_scrub_empties_cost_margin_and_metric_cards() -> None:
    node = {
        "net_sales": 100,
        "items": [
            {"sku": "A", "unit_cost": 5, "margin_pct": 40, "gross_margin_amount": 40, "units": 3}
        ],
        "headline": [
            {"key": "gross_margin", "value": 41, "change_pct": 2},
            {"key": "net_sales", "value": 100},
        ],
        "cost_note": "kept: nested text is not a number",
    }
    out = scrub(node)
    assert out["net_sales"] == 100
    assert out["items"] == [
        {"sku": "A", "unit_cost": None, "margin_pct": None, "gross_margin_amount": None, "units": 3}
    ]
    assert out["headline"][0] == {"key": "gross_margin", "value": None, "change_pct": None}
    assert out["headline"][1] == {"key": "net_sales", "value": 100}
    assert out["cost_note"] is None  # any field named cost is hidden, text included: safer


def _join(
    client: TestClient, ws: str, owner: dict[str, str], who: dict[str, str], role: str, persona: str
) -> None:
    inv = client.post(
        f"/api/v1/workspaces/{ws}/invitations",
        json={"role": role, "persona": persona},
        headers=owner,
    )
    assert (
        client.post(
            "/api/v1/invitations/accept", json={"token": inv.json()["token"]}, headers=who
        ).status_code
        == 200
    )


def test_ops_manager_sees_sales_but_not_margin_and_cannot_open_customers(
    client: TestClient, make_user
) -> None:
    owner, ws = make_shop(client, make_user, "m@shop.in", shop_csv(60))
    ops = make_user("ops@shop.in")
    _join(client, ws, owner, ops, "admin", "ops_manager")
    base = f"/api/v1/workspaces/{ws}"
    own = client.get(f"{base}/analytics/products", headers=owner).json()
    masked = client.get(f"{base}/analytics/products", headers=ops).json()
    assert masked["items"][0]["net"] == own["items"][0]["net"]  # sales are untouched
    assert any(i.get("margin_pct") is not None for i in own["items"])
    assert all(
        i.get("margin_pct") is None and i.get("margin_amount") is None for i in masked["items"]
    )
    ov = client.get(f"{base}/analytics/overview", headers=ops).json()
    cards = {c["key"]: c for c in ov["headline"] + ov["secondary"]}
    assert cards["net_sales"]["value"] is not None
    assert cards["gross_margin"]["value"] is None
    assert client.get(f"{base}/analytics/customers/summary", headers=ops).status_code == 403
    assert client.get(f"{base}/analytics/customers/summary", headers=owner).status_code == 200


def test_analyst_keeps_margin(client: TestClient, make_user) -> None:
    owner, ws = make_shop(client, make_user, "m2@shop.in", shop_csv(60))
    an = make_user("an@shop.in")
    _join(client, ws, owner, an, "analyst", "analyst")
    items = client.get(f"/api/v1/workspaces/{ws}/analytics/products", headers=an).json()["items"]
    assert any(i.get("margin_pct") is not None for i in items)
