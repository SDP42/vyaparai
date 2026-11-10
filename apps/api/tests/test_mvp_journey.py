"""The MVP journey from the blueprint, end to end, as one signed-in user.

sign in with the cookie session -> workspace -> import a sales file -> trusted numbers ->
customers and products -> forecast -> alerts -> digest -> stock advice -> invite a teammate.
If this passes, the product works from the first upload to the first decision.
"""

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD
from tests.test_forecast_api import shop_csv
from tests.test_intelligence_api import make_shop

CSRF = {"X-Requested-With": "vyapar"}


def test_a_new_owner_can_go_from_sign_up_to_decisions(client: TestClient) -> None:
    # 1. Sign up, sign in (HttpOnly cookie), and renew the short access token from it
    email = "journey@shop.in"
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Meera", "password": PASSWORD},
        ).status_code
        == 201
    )
    login = client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
    assert login.status_code == 200
    renewed = client.post("/api/v1/auth/refresh", headers=CSRF).json()["access_token"]
    h = {"Authorization": f"Bearer {renewed}"}

    # 2. Workspace + import (make_shop runs upload -> map -> validate -> import)
    def signed_in(_email: str, _name: str = "") -> dict[str, str]:
        return h

    h, ws = make_shop(client, signed_in, email, shop_csv(84))
    base = f"/api/v1/workspaces/{ws}"

    # 3. Trusted numbers
    ov = client.get(f"{base}/analytics/overview", headers=h)
    assert ov.status_code == 200
    assert ov.json()["headline"]

    # 4. Customers and products
    assert client.get(f"{base}/analytics/customers/summary", headers=h).status_code == 200
    assert client.get(f"{base}/analytics/products", headers=h).status_code == 200

    # 5. Forecast (a background job that must succeed)
    job = client.post(f"{base}/forecasts/run", headers=h)
    assert job.status_code == 202
    done = client.get(f"{base}/jobs/{job.json()['id']}", headers=h).json()
    assert done["status"] == "succeeded", done
    latest = client.get(f"{base}/forecasts/latest", headers=h).json()
    assert latest["kpis"]["units_next"] > 0

    # 6. Alerts, digest and stock advice answer without error
    assert client.get(f"{base}/alerts", headers=h).status_code == 200
    assert client.get(f"{base}/digests/preview", headers=h).status_code == 200
    assert client.get(f"{base}/inventory/overview", headers=h).status_code == 200

    # 7. Invite a teammate, who joins with the chosen role
    mate = {"Authorization": "Bearer " + _second_user(client)}
    inv = client.post(f"{base}/invitations", json={"role": "analyst"}, headers=h).json()
    joined = client.post("/api/v1/invitations/accept", json={"token": inv["token"]}, headers=mate)
    assert joined.status_code == 200
    assert client.get(f"{base}/forecasts/latest", headers=mate).status_code == 200

    # 8. Sign out everywhere ends the session for good
    assert client.post("/api/v1/auth/logout-all", headers={**CSRF, **h}).status_code == 204
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def _second_user(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": "mate@shop.in", "full_name": "Arjun", "password": PASSWORD},
    )
    r = client.post("/api/v1/auth/login", data={"username": "mate@shop.in", "password": PASSWORD})
    return str(r.json()["access_token"])
