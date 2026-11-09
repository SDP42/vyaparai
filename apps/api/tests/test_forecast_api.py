# ruff: noqa: E501  (CSV fixture rows are clearer on one line)
"""Forecast endpoints end to end on a shop whose demand pattern is known."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.test_intelligence_api import make_shop

WEEK = [8, 8, 8, 9, 10, 16, 14]  # units per weekday, Monday first; 73 a week


def shop_csv(days: int) -> str:
    start = date(2026, 8, 3)  # a Monday
    lines = [
        "Bill No,Bill Date,Item Code,Item Name,Category,Qty,Rate,Discount,Cost,Customer,State,City,Channel,Status"
    ]
    for i in range(days):
        d = start + timedelta(days=i)
        day = d.strftime("%d/%m/%Y")
        lines.append(
            f"A{i},{day},SKU-A,Weekly,Cat,{WEEK[d.weekday()]},100,0,60,C1,MH,Pune,Store,Paid"
        )
        lines.append(f"B{i},{day},SKU-B,Steady,Cat,5,50,0,30,C2,MH,Pune,Store,Paid")
        if i % 9 == 0:
            lines.append(f"C{i},{day},SKU-C,Rare,Cat,1,200,0,120,C3,MH,Pune,Store,Paid")
    return "\n".join(lines) + "\n"


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "fc@shop.in", shop_csv(84))


def url(shop, path: str) -> str:
    return f"/api/v1/workspaces/{shop[1]}/forecasts{path}"


def run_forecast(client: TestClient, shop) -> dict:
    h = shop[0]
    job = client.post(url(shop, "/run"), headers=h)
    assert job.status_code == 202
    done = client.get(f"/api/v1/workspaces/{shop[1]}/jobs/{job.json()['id']}", headers=h).json()
    assert done["status"] == "succeeded", done
    return done


def test_nothing_before_the_first_run(client: TestClient, shop) -> None:
    r = client.get(url(shop, "/latest"), headers=shop[0]).json()
    assert r["has_forecast"] is False
    assert r["can_forecast"] is True
    assert r["history_days"] == 84
    assert client.get(url(shop, "/products"), headers=shop[0]).status_code == 404


def test_run_then_read_overview(client: TestClient, shop) -> None:
    done = run_forecast(client, shop)
    assert done["job_type"] == "forecast_training"
    assert done["result"]["series"] == 3
    r = client.get(url(shop, "/latest"), headers=shop[0]).json()
    assert r["run"]["horizon"] == 14
    assert r["run"]["history_days"] == 84
    assert r["run"]["as_of"] == "2026-10-25"
    assert r["stale"] is False
    k = r["kpis"]
    assert k["units_next_low"] <= k["units_next"] <= k["units_next_high"]
    # last 14 days actual: 2 weeks x (73 + 5 x 7) = 216, plus rare product
    assert 200 <= k["units_last"] <= 220
    assert 170 <= k["units_next"] <= 260
    assert r["accuracy"]["wape"] < 0.2
    assert r["accuracy"]["windows"] >= 1
    assert sum(r["confidence_counts"].values()) == 3
    assert len(r["totals"]["forecast"]) == 14
    assert any("festive season" in w for w in r["warnings"])  # peak on 8 Nov, under a year of data
    assert r["model_card"]["assumptions"]


def test_product_list_detail_and_filters(client: TestClient, shop) -> None:
    run_forecast(client, shop)
    h = shop[0]
    page = client.get(url(shop, "/products"), headers=h).json()
    assert page["total"] == 3
    assert page["items"][0]["sku"] == "SKU-A"  # biggest forecast first
    a = page["items"][0]
    assert 110 <= a["units_next"] <= 185  # true value 146
    assert len(a["spark"]) == 28 + 14
    one = client.get(url(shop, "/products"), params={"search": "steady"}, headers=h).json()
    assert [i["sku"] for i in one["items"]] == ["SKU-B"]
    assert (
        client.get(url(shop, "/products"), params={"model": "nope"}, headers=h).status_code == 422
    )
    d = client.get(url(shop, "/products/SKU-A"), headers=h).json()
    assert len(d["data"]["p50"]) == 14
    assert len(d["data"]["hist"]) == 84
    assert d["data"]["backtest"]
    assert all(
        lo <= m <= hi
        for lo, m, hi in zip(d["data"]["p10"], d["data"]["p50"], d["data"]["p90"], strict=True)
    )
    assert client.get(url(shop, "/products/NOPE"), headers=h).status_code == 404


def test_csv_export(client: TestClient, shop) -> None:
    run_forecast(client, shop)
    r = client.get(url(shop, "/export.csv"), headers=shop[0])
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("sku,product,category,date,p10,p50,p90")
    assert len(lines) == 1 + 3 * 14


def test_stale_flag_after_new_sales(client: TestClient, shop, make_user) -> None:
    run_forecast(client, shop)
    from tests.test_ingestion import full_flow

    h, ws_id = shop
    more = shop_csv(86).replace(
        "A0,", "ZZ0,"
    )  # new bill ids for old days are skipped; days 84-85 are new
    _, base, _ = full_flow(client, h, ws_id, more.encode(), "more.csv")
    job = client.post(f"{base}/import", headers=h).json()
    assert (
        client.get(f"/api/v1/workspaces/{ws_id}/jobs/{job['id']}", headers=h).json()["status"]
        == "succeeded"
    )
    assert client.get(url(shop, "/latest"), headers=h).json()["stale"] is True


def test_not_enough_data_is_refused(client: TestClient, make_user) -> None:
    tiny = make_shop(client, make_user, "tiny@shop.in", shop_csv(5))
    r = client.post(url(tiny, "/run"), headers=tiny[0])
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "not_enough_data"
    latest = client.get(url(tiny, "/latest"), headers=tiny[0]).json()
    assert latest["can_forecast"] is False


def test_other_workspaces_cannot_see_it(client: TestClient, shop, make_user) -> None:
    run_forecast(client, shop)
    stranger = make_user("stranger@x.in", "Stranger")
    assert client.get(url(shop, "/latest"), headers=stranger).status_code == 404
    assert client.post(url(shop, "/run"), headers=stranger).status_code == 404


def test_running_twice_keeps_only_recent_runs(client: TestClient, shop) -> None:
    for _ in range(3):
        run_forecast(client, shop)
    r = client.get(url(shop, "/latest"), headers=shop[0]).json()
    assert r["run"]["n_series"] == 3


def test_a_lost_job_does_not_block_new_runs(client: TestClient, shop, db_session_factory) -> None:
    import uuid
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.models.dataset import Job, JobStatus, JobType

    with db_session_factory() as db:
        db.add(
            Job(
                workspace_id=uuid.UUID(shop[1]),
                job_type=JobType.FORECAST_TRAINING,
                status=JobStatus.RUNNING,
                created_at=datetime.now(UTC) - timedelta(minutes=30),
            )
        )
        db.commit()
    done = run_forecast(client, shop)  # would return the stuck job if it were not recovered
    assert done["status"] == "succeeded"
    with db_session_factory() as db:
        statuses = db.scalars(
            select(Job.status).where(Job.job_type == JobType.FORECAST_TRAINING)
        ).all()
    assert JobStatus.FAILED in statuses


# ---------------------------------------------------------------- registry, options, scheduling


def runs(client: TestClient, shop) -> list[dict]:
    return client.get(url(shop, "/runs"), headers=shop[0]).json()


def test_runs_are_numbered_and_the_newest_is_active(client: TestClient, shop) -> None:
    run_forecast(client, shop)
    run_forecast(client, shop)
    r = runs(client, shop)
    assert [x["version"] for x in r] == [2, 1]
    assert [x["status"] for x in r] == ["active", "superseded"]
    assert r[0]["models"]
    assert r[0]["wape"] is not None
    assert client.get(url(shop, "/latest"), headers=shop[0]).json()["run"]["version"] == 2


def test_rolling_back_to_an_older_version(client: TestClient, shop, make_user) -> None:
    run_forecast(client, shop)
    run_forecast(client, shop)
    v1 = runs(client, shop)[1]
    r = client.post(url(shop, f"/runs/{v1['id']}/activate"), headers=shop[0]).json()
    assert r["status"] == "active"
    assert "by hand" in r["note"]
    assert [x["status"] for x in runs(client, shop)] == ["superseded", "active"]
    assert client.get(url(shop, "/latest"), headers=shop[0]).json()["run"]["version"] == 1
    stranger = make_user("rb@x.in", "R")
    assert client.post(url(shop, f"/runs/{v1['id']}/activate"), headers=stranger).status_code == 404
    assert (
        client.post(
            url(shop, f"/runs/{'0' * 8}-0000-0000-0000-{'0' * 12}/activate"), headers=shop[0]
        ).status_code
        == 404
    )


def test_run_options_are_validated_and_recorded(client: TestClient, shop) -> None:
    assert (
        client.post(url(shop, "/run"), params={"peak_uplift_pct": 80}, headers=shop[0]).status_code
        == 422
    )
    job = client.post(
        url(shop, "/run"), params={"peak_uplift_pct": 20, "tune": "true"}, headers=shop[0]
    ).json()
    done = client.get(f"/api/v1/workspaces/{shop[1]}/jobs/{job['id']}", headers=shop[0]).json()
    assert done["status"] == "succeeded"
    assert done["result"]["options"] == {"tune": True, "peak_uplift_pct": 20}
    assert done["result"]["version"] == 1
    assert runs(client, shop)[0]["options"] == {"tune_trials": 12, "peak_uplift_pct": 20}


def seed_run(db, ws, version: int, gate: bool | None, status: str):
    import uuid
    from datetime import date as _d

    from app.models.forecast import ForecastRun

    db.add(
        ForecastRun(
            workspace_id=uuid.UUID(ws),
            version=version,
            status=status,
            as_of=_d(2026, 10, 25),
            horizon=14,
            history_days=84,
            n_series=1,
            seconds=1.0,
            summary={"accuracy": {"gate_passed": gate}},
        )
    )
    db.commit()


def test_ship_gate_keeps_the_good_version_when_a_worse_one_arrives(
    shop, db_session_factory
) -> None:
    import uuid

    from app.models.forecast import ForecastRun
    from app.services.forecasting import service

    ws = uuid.UUID(shop[1])
    with db_session_factory() as db:
        assert service._registry_decision(db, ws, {"accuracy": {"gate_passed": True}}) == (
            1,
            "active",
            None,
        )
        seed_run(db, shop[1], 1, True, "active")
        version, status, note = service._registry_decision(
            db, ws, {"accuracy": {"gate_passed": False}}
        )
        assert (version, status) == (2, "rejected")
        assert "version 1 stays active" in note
        assert db.get(ForecastRun, db.query(ForecastRun).one().id).status == "active"  # untouched
        # a new run that also passes replaces it
        version, status, note = service._registry_decision(
            db, ws, {"accuracy": {"gate_passed": True}}
        )
        assert (version, status, note) == (2, "active", None)
        assert db.query(ForecastRun).one().status == "superseded"


def test_a_failing_run_is_not_active_when_the_active_one_passed(shop, db_session_factory) -> None:
    from app.services.forecasting import service

    with db_session_factory() as db:
        seed_run(db, shop[1], 1, True, "active")
        import uuid

        v, st, _ = service._registry_decision(
            db, uuid.UUID(shop[1]), {"accuracy": {"gate_passed": False}}
        )
        assert st == "rejected"
        assert v == 2


def test_scheduled_run_only_rebuilds_when_sales_moved_on(
    client: TestClient, shop, db_session_factory
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.services.forecasting import service
    from tests.test_ingestion import full_flow

    with db_session_factory() as db:
        first = service.run_stale(db)  # no forecast yet: builds one
        assert len(first) == 1
        assert first[0]["status"] == "succeeded"
        assert service.run_stale(db) == []  # nothing new since
    assert [x["version"] for x in runs(client, shop)] == [1]

    h, ws_id = shop
    _, base, _ = full_flow(
        client, h, ws_id, shop_csv(86).replace("A0,", "ZZ0,").encode(), "more.csv"
    )
    job = client.post(f"{base}/import", headers=h).json()
    assert (
        client.get(f"/api/v1/workspaces/{ws_id}/jobs/{job['id']}", headers=h).json()["status"]
        == "succeeded"
    )

    with db_session_factory() as db:
        too_soon = service.run_stale(db, datetime.now(UTC) + timedelta(hours=1))
        assert too_soon == []  # new sales, but the last run was minutes ago
        later = service.run_stale(db, datetime.now(UTC) + timedelta(hours=25))
        assert len(later) == 1
    assert [x["version"] for x in runs(client, shop)] == [2, 1]
    assert client.get(url(shop, "/latest"), headers=h).json()["stale"] is False


def test_scheduled_run_keeps_the_owners_festive_adjustment(
    client: TestClient, shop, db_session_factory
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.services.forecasting import service
    from tests.test_ingestion import full_flow

    client.post(url(shop, "/run"), params={"peak_uplift_pct": 15}, headers=shop[0])
    h, ws_id = shop
    _, base, _ = full_flow(
        client, h, ws_id, shop_csv(86).replace("A0,", "ZZ0,").encode(), "more.csv"
    )
    client.post(f"{base}/import", headers=h)
    with db_session_factory() as db:
        service.run_stale(db, datetime.now(UTC) + timedelta(hours=25))
    assert runs(client, shop)[0]["options"]["peak_uplift_pct"] == 15


def test_events_are_tested_and_the_region_is_reported(client: TestClient, shop) -> None:
    client.put(
        f"/api/v1/workspaces/{shop[1]}/events/region",
        json={"state": "Maharashtra"},
        headers=shop[0],
    )
    run_forecast(client, shop)
    r = client.get(url(shop, "/latest"), headers=shop[0]).json()
    ev = r["signals"]["events"]
    assert ev["status"] == "ok"
    assert ev["state"] == "Maharashtra"
    assert ev["zones"] == ["west"]
    assert ev["region_known"] is True
    assert isinstance(ev["used"], bool)  # the backtest decides whether events help this shop
    groups = {g["group"]: g for g in r["accuracy"]["covariates"]["groups"]}
    assert groups["events"]["names"] == ["cricket", "event_intensity"]
    assert any(
        "festive season" in w and "Diwali" in w for w in r["warnings"]
    )  # names the actual festival
