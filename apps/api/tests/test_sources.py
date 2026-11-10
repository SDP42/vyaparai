# ruff: noqa: E501
"""Link sources: safety of the fetch, scheduling, de-duplication and remembered column mappings."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services import mapping_profiles, safe_fetch, sources
from tests.test_ingestion import upload

HEAD = "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"
GOOGLE = "https://docs.google.com/spreadsheets/d/AbC123_-x/export?format=csv"


def csv_bytes(n: int, start: int = 1) -> bytes:
    rows = [HEAD] + [
        f"B{i},{(date(2026, 10, 1) + timedelta(days=i % 20)):%d/%m/%Y},SKU-{i % 4},Item {i % 4},Cat,{1 + i % 3},100,0,60,,,,Store,Paid"
        for i in range(start, start + n)
    ]
    return ("\n".join(rows) + "\n").encode()


def public(host: str, port: int) -> list[str]:
    return ["142.250.0.1"]  # a public address


# ---------------------------------------------------------------- the link is checked before anything is fetched


@pytest.mark.parametrize(
    ("url", "why"),
    [
        ("http://docs.google.com/spreadsheets/d/x/export?format=csv", "https"),
        ("ftp://docs.google.com/x", "https"),
        ("file:///etc/passwd", "https"),
        ("https://user:pass@docs.google.com/x", "user name"),
        ("https://docs.google.com:8443/x", "port"),
        ("https://127.0.0.1/x", "numeric"),
        ("https://169.254.169.254/latest/meta-data", "numeric"),
        ("https://[::1]/x", "numeric"),
        ("https://localhost/x", "allowed list"),
        ("https://evil.example.com/x", "allowed list"),
        ("https://docs.google.com.evil.com/x", "allowed list"),
        ("https://notgoogleusercontent.com/x", "allowed list"),
    ],
)
def test_unsafe_links_are_refused(url: str, why: str) -> None:
    with pytest.raises(safe_fetch.UnsafeUrlError, match=why):
        safe_fetch.check_url(url, public)


def test_allowed_hosts_pass_and_wildcards_need_a_subdomain() -> None:
    p, ip, port = safe_fetch.check_url(GOOGLE, public)
    assert (p.hostname, ip, port) == ("docs.google.com", "142.250.0.1", 443)
    safe_fetch.check_url("https://doc-0c-abc.googleusercontent.com/x", public)
    with pytest.raises(safe_fetch.UnsafeUrlError):
        safe_fetch.check_url(
            "https://googleusercontent.com/x", public
        )  # the wildcard needs a subdomain


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.1.2.3",
        "192.168.0.5",
        "172.16.9.9",
        "169.254.169.254",
        "::1",
        "fe80::1",
        "fd00::5",
        "100.64.0.1",
        "0.0.0.0",  # noqa: S104
        "224.0.0.1",
    ],
)
def test_a_name_that_resolves_to_an_internal_address_is_refused(ip: str) -> None:
    with pytest.raises(safe_fetch.UnsafeUrlError, match="private or internal"):
        safe_fetch.check_url(GOOGLE, lambda h, p: [ip])


def test_one_bad_address_among_good_ones_is_enough_to_refuse() -> None:
    with pytest.raises(safe_fetch.UnsafeUrlError):
        safe_fetch.check_url(GOOGLE, lambda h, p: ["142.250.0.1", "10.0.0.8"])


def test_an_administrator_can_open_any_public_host_but_never_internal_ones(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "source_allow_any_public_host", True)
    safe_fetch.check_url("https://files.example.org/sales.csv", public)
    with pytest.raises(safe_fetch.UnsafeUrlError):
        safe_fetch.check_url("https://files.example.org/sales.csv", lambda h, p: ["10.0.0.1"])


def test_google_sheet_links_become_csv_export_links() -> None:
    n = safe_fetch.normalise_url
    assert (
        n("https://docs.google.com/spreadsheets/d/AbC123_-x/edit#gid=77")
        == "https://docs.google.com/spreadsheets/d/AbC123_-x/export?format=csv&gid=77"
    )
    assert (
        n("https://docs.google.com/spreadsheets/d/AbC123_-x/edit?usp=sharing")
        == "https://docs.google.com/spreadsheets/d/AbC123_-x/export?format=csv"
    )
    assert n(GOOGLE) == GOOGLE  # already an export link
    assert (
        n("https://docs.google.com/spreadsheets/d/e/2PACX-x/pub?output=csv")
        == "https://docs.google.com/spreadsheets/d/e/2PACX-x/pub?output=csv"
    )
    assert (
        n("https://dl.dropboxusercontent.com/s/x/sales.csv")
        == "https://dl.dropboxusercontent.com/s/x/sales.csv"
    )


# ---------------------------------------------------------------- fetching


def resp(status=200, body=b"a,b\n1,2\n", **headers):
    return safe_fetch.Response(status, {k.replace("_", "-"): v for k, v in headers.items()}, body)


def fetch_with(*responses, resolver=public, max_bytes=1000):
    seen = []
    it = iter(responses)

    def requester(p, ip, port, timeout, cap):
        seen.append((p.hostname, ip))
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r

    out = safe_fetch.fetch(GOOGLE, max_bytes=max_bytes, resolver=resolver, requester=requester)
    return out, seen


def test_a_good_csv_is_returned_with_its_hash() -> None:
    (body, digest), seen = fetch_with(resp(content_type="text/csv; charset=utf-8"))
    assert body == b"a,b\n1,2\n"
    assert len(digest) == 64
    assert seen == [("docs.google.com", "142.250.0.1")]  # connected to the validated address


def test_a_redirect_to_an_internal_address_is_refused() -> None:
    resolver = lambda h, p: ["10.0.0.9"] if h == "docs.google.com" else ["142.250.0.1"]  # noqa: E731
    with pytest.raises(safe_fetch.UnsafeUrlError):
        fetch_with(
            resp(302, location="https://evil.googleusercontent.com/x"),
            resolver=lambda h, p: ["10.0.0.9"] if "evil" in h else ["142.250.0.1"],
        )
    with pytest.raises(safe_fetch.UnsafeUrlError):
        fetch_with(resp(302, location="http://169.254.169.254/latest"))
    with pytest.raises(safe_fetch.UnsafeUrlError):
        fetch_with(resp(302, location="https://localhost/admin"))
    assert resolver  # (kept for readability)


def test_redirects_to_allowed_hosts_are_followed_but_capped() -> None:
    (body, _), seen = fetch_with(
        resp(302, location="https://doc-1.googleusercontent.com/x"), resp(content_type="text/csv")
    )
    assert body.startswith(b"a,b")
    assert [h for h, _ in seen] == ["docs.google.com", "doc-1.googleusercontent.com"]
    loop = [resp(302, location="https://docs.google.com/again")] * 5
    with pytest.raises(safe_fetch.FetchError, match="too many times"):
        fetch_with(*loop)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (resp(403), "private"),
        (resp(401), "private"),
        (resp(404), "not found"),
        (resp(500), "error"),
        (resp(content_type="text/html", body=b"<html>sign in</html>"), "web page"),
        (resp(body=b"<!DOCTYPE html><html>"), "web page"),
        (resp(content_type="application/pdf"), "CSV or Excel"),
        (resp(body=b""), "empty"),
        (resp(body=b"x" * 2000), "larger"),
    ],
)
def test_bad_responses_give_a_plain_message(response, message) -> None:
    with pytest.raises(safe_fetch.FetchError, match=message):
        fetch_with(response)


def test_network_failures_are_reported_without_internals() -> None:
    with pytest.raises(safe_fetch.FetchError) as e:
        fetch_with(TimeoutError("connect timed out to 142.250.0.1"))
    assert "142.250" not in str(e.value)
    assert "could not be reached" in str(e.value)


# ---------------------------------------------------------------- remembered mappings


def test_the_fingerprint_ignores_order_case_and_punctuation() -> None:
    a = mapping_profiles.fingerprint(["Bill No", "Bill Date", "Qty"])
    assert a == mapping_profiles.fingerprint(["qty", "BILL_DATE", "bill-no"])
    assert a != mapping_profiles.fingerprint(["Bill No", "Bill Date", "Quantity"])


ODD = "Invoice #,Sold On,Product Code,Description,Units,Unit Price\n"
ODD_ROWS = ["I1,03/10/2026,P1,Widget,2,50", "I2,04/10/2026,P2,Gadget,1,80"]


def odd(n: int = 2) -> bytes:
    return (ODD + "\n".join(ODD_ROWS[:n]) + "\n").encode()


@pytest.fixture
def ws(client: TestClient, make_user):
    h = make_user("src@shop.in", "Owner")
    wid = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    return h, wid


def test_a_confirmed_mapping_is_remembered_for_the_same_layout(client: TestClient, ws) -> None:
    h, wid = ws
    first = upload(client, h, wid, odd(), "a.csv").json()
    assert first["column_mapping"].get("remembered") is None
    fields = {
        "order_id": "Invoice #",
        "order_date": "Sold On",
        "sku": "Product Code",
        "product_name": "Description",
        "quantity": "Units",
        "unit_price": "Unit Price",
    }
    r = client.put(
        f"/api/v1/workspaces/{wid}/datasets/{first['id']}/mapping",
        json={"fields": fields, "date_order": "dmy"},
        headers=h,
    )
    assert r.status_code == 200
    second = upload(
        client, h, wid, odd() + b"I9,05/10/2026,P3,Gizmo,1,10\n", "b.csv"
    ).json()  # a new file with the same columns
    cm = second["column_mapping"]
    assert cm["remembered"] is True
    assert cm["fields"] == fields
    assert cm["date_order"] == "dmy"
    other = upload(
        client,
        h,
        wid,
        HEAD.encode() + b"\nX1,01/10/2026,S,Item,Cat,1,10,0,5,,,,Store,Paid\n",
        "c.csv",
    ).json()
    assert (
        other["column_mapping"].get("remembered") is None
    )  # a different layout is not assumed to match


def test_a_remembered_mapping_is_not_used_if_a_column_disappears(
    client: TestClient, ws, db_session_factory
) -> None:
    import uuid

    wid = ws[1]
    with db_session_factory() as db:
        mapping_profiles.remember(
            db, uuid.UUID(wid), ["a", "b"], {"fields": {"sku": "gone"}, "date_order": "dmy"}, "x"
        )
        db.commit()
        prof = mapping_profiles.find(db, uuid.UUID(wid), ["a", "b"])
        assert mapping_profiles.usable(prof, ["a", "b"]) is None


# ---------------------------------------------------------------- sources: API


def src_url(ws, path=""):
    return f"/api/v1/workspaces/{ws[1]}/sources{path}"


def add(client, ws, **kw):
    body = {
        "name": "Billing sheet",
        "url": "https://docs.google.com/spreadsheets/d/AbC123_-x/edit#gid=5",
        "schedule": "daily",
        **kw,
    }
    return client.post(src_url(ws), json=body, headers=ws[0])


def test_create_list_update_delete_and_limits(client: TestClient, ws, make_user) -> None:
    r = add(client, ws)
    assert r.status_code == 201
    s = r.json()
    assert (
        s["url"] == "https://docs.google.com/spreadsheets/d/AbC123_-x/export?format=csv&gid=5"
    )  # normalised
    assert s["last_status"] == "never"
    assert [x["id"] for x in client.get(src_url(ws), headers=ws[0]).json()] == [s["id"]]
    p = client.patch(
        src_url(ws, f"/{s['id']}"),
        json={"schedule": "hourly", "name": "Sheet 2", "enabled": False},
        headers=ws[0],
    ).json()
    assert (p["schedule"], p["name"], p["enabled"]) == ("hourly", "Sheet 2", False)
    assert add(client, ws, url="http://evil.example.com/x").status_code == 422
    assert add(client, ws, url="https://evil.example.com/x").status_code == 422
    assert add(client, ws, schedule="weekly").status_code == 422
    for _ in range(4):
        add(client, ws)
    assert add(client, ws).status_code == 422  # five links at most
    assert client.delete(src_url(ws, f"/{s['id']}"), headers=ws[0]).status_code == 204
    stranger = make_user("x@x.in", "X")
    assert client.get(src_url(ws), headers=stranger).status_code == 404
    assert client.delete(src_url(ws, f"/{s['id']}"), headers=ws[0]).status_code == 404


# ---------------------------------------------------------------- sources: running


def engine_of(db_session_factory):
    return db_session_factory.kw["bind"]


def summary(client, ws):
    return client.get(f"/api/v1/workspaces/{ws[1]}/data-summary", headers=ws[0]).json()


def test_first_run_imports_then_unchanged_then_only_new_orders(
    client: TestClient, ws, db_session_factory
) -> None:
    sid = add(client, ws).json()["id"]
    import uuid

    eng = engine_of(db_session_factory)
    sources.run_source(eng, uuid.UUID(sid), fetcher=lambda url, max_bytes: (csv_bytes(10), "h1"))
    s = client.get(src_url(ws), headers=ws[0]).json()[0]
    assert s["last_status"] == "ok"
    assert s["last_new_orders"] == 10
    assert "10 new orders added" in s["last_message"]
    assert summary(client, ws)["orders"] == 10

    sources.run_source(
        eng, uuid.UUID(sid), fetcher=lambda url, max_bytes: (csv_bytes(10), "h1")
    )  # same file
    s = client.get(src_url(ws), headers=ws[0]).json()[0]
    assert s["last_status"] == "unchanged"
    assert summary(client, ws)["orders"] == 10

    sources.run_source(
        eng, uuid.UUID(sid), fetcher=lambda url, max_bytes: (csv_bytes(13), "h2")
    )  # three new bills
    s = client.get(src_url(ws), headers=ws[0]).json()[0]
    assert s["last_status"] == "ok"
    assert s["last_new_orders"] == 3
    assert "10 already known" in s["last_message"]
    assert summary(client, ws)["orders"] == 13  # no duplicates
    runs = client.get(src_url(ws, f"/{sid}/runs"), headers=ws[0]).json()
    assert [r["status"] for r in runs] == ["ok", "unchanged", "ok"]


def test_a_file_that_cannot_be_matched_fails_with_a_clear_next_step(
    client: TestClient, ws, db_session_factory
) -> None:
    import uuid

    sid = add(client, ws).json()["id"]
    sources.run_source(
        engine_of(db_session_factory),
        uuid.UUID(sid),
        fetcher=lambda url, max_bytes: (b"foo,bar\n1,2\n", "hx"),
    )
    s = client.get(src_url(ws), headers=ws[0]).json()[0]
    assert s["last_status"] == "failed"
    assert "Upload this file once by hand" in s["last_message"]
    assert s["failures"] == 1
    assert summary(client, ws)["orders"] == 0


def test_after_one_manual_confirmation_the_source_recognises_the_layout(
    client: TestClient, ws, db_session_factory
) -> None:
    import uuid

    h, wid = ws
    first = upload(client, h, wid, odd(), "a.csv").json()
    fields = {
        "order_id": "Invoice #",
        "order_date": "Sold On",
        "sku": "Product Code",
        "product_name": "Description",
        "quantity": "Units",
        "unit_price": "Unit Price",
    }
    client.put(
        f"/api/v1/workspaces/{wid}/datasets/{first['id']}/mapping",
        json={"fields": fields, "date_order": "dmy"},
        headers=h,
    )
    sid = add(client, ws).json()["id"]
    sources.run_source(
        engine_of(db_session_factory),
        uuid.UUID(sid),
        fetcher=lambda url, max_bytes: (odd() + b"I7,06/10/2026,P9,Thing,3,20\n", "h9"),
    )
    s = client.get(src_url(ws), headers=h).json()[0]
    assert s["last_status"] == "ok", s["last_message"]
    assert s["last_new_orders"] == 3  # I1, I2 and I7


def test_five_failures_in_a_row_pause_the_source(
    client: TestClient, ws, db_session_factory
) -> None:
    import uuid

    sid = add(client, ws).json()["id"]
    eng = engine_of(db_session_factory)

    def boom(url, max_bytes):
        raise safe_fetch.FetchError("The link was not found.")

    for _ in range(5):
        sources.run_source(eng, uuid.UUID(sid), fetcher=boom)
    s = client.get(src_url(ws), headers=ws[0]).json()[0]
    assert s["enabled"] is False
    assert "Paused after 5 failed tries" in s["last_message"]
    client.patch(src_url(ws, f"/{sid}"), json={"enabled": True}, headers=ws[0])
    assert (
        client.get(src_url(ws), headers=ws[0]).json()[0]["failures"] == 0
    )  # resuming starts fresh


def test_the_schedule_decides_what_is_due() -> None:
    from app.models.source import ImportSource

    now = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)

    def src(**kw):
        base = {
            "schedule": "daily",
            "enabled": True,
            "last_status": "ok",
            "last_run_at": now - timedelta(hours=30),
        }
        return ImportSource(**{**base, **kw})

    assert sources.is_due(src(), now)
    assert not sources.is_due(src(last_run_at=now - timedelta(hours=5)), now)
    assert sources.is_due(src(schedule="hourly", last_run_at=now - timedelta(minutes=70)), now)
    assert not sources.is_due(src(schedule="hourly", last_run_at=now - timedelta(minutes=20)), now)
    assert not sources.is_due(src(schedule="manual"), now)
    assert not sources.is_due(src(enabled=False), now)
    assert not sources.is_due(src(last_status="running"), now)
    assert sources.is_due(src(last_run_at=None), now)  # never run


def test_run_due_only_runs_sources_that_are_due(client: TestClient, ws, db_session_factory) -> None:
    add(client, ws, schedule="daily")
    add(client, ws, schedule="manual", name="By hand")
    out = sources.run_due(
        engine_of(db_session_factory), fetcher=lambda url, max_bytes: (csv_bytes(4), "hh")
    )
    assert len(out) == 1
    assert out[0]["status"] == "ok"
    assert (
        sources.run_due(
            engine_of(db_session_factory), fetcher=lambda url, max_bytes: (csv_bytes(4), "hh")
        )
        == []
    )  # not due again


def test_run_now_endpoint_uses_the_safe_fetcher(client: TestClient, ws, monkeypatch) -> None:
    seen = {}

    def fake(url, *, max_bytes, resolver=None, requester=None):
        seen["url"], seen["max"] = url, max_bytes
        return csv_bytes(5), "hz"

    monkeypatch.setattr(safe_fetch, "fetch", fake)
    sid = add(client, ws).json()["id"]
    assert client.post(src_url(ws, f"/{sid}/run"), headers=ws[0]).status_code == 202
    s = client.get(src_url(ws), headers=ws[0]).json()[0]
    assert s["last_status"] == "ok"
    assert seen["url"].startswith("https://docs.google.com/")
    assert seen["max"] == get_settings().max_upload_size_mb * 1024 * 1024


def test_a_failing_source_raises_an_alert(client: TestClient, ws, db_session_factory) -> None:
    import uuid

    sid = add(client, ws).json()["id"]
    eng = engine_of(db_session_factory)

    def boom(url, max_bytes):
        raise safe_fetch.FetchError("The link was not found.")

    for _ in range(2):
        sources.run_source(eng, uuid.UUID(sid), fetcher=boom)
    from app.models.workspace import Workspace
    from app.services import alerts

    with db_session_factory() as db:
        found = alerts.rule_sources(db, uuid.UUID(ws[1]))
        assert db.get(Workspace, uuid.UUID(ws[1])) is not None
    assert len(found) == 1
    assert found[0]["rule"] == "source_failing"
    assert "not found" in found[0]["detail"]
