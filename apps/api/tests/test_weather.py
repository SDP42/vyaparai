"""Weather cache, fallbacks, licence rule and the forecast integration (no real network)."""

from datetime import date, timedelta
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings
from app.models.weather import WeatherDaily
from app.services import weather
from tests.test_forecast_api import run_forecast, shop_csv
from tests.test_intelligence_api import make_shop

TODAY = date(2026, 11, 9)


def temp_on(d: date) -> float:
    return 30 + 4 * np.sin(d.toordinal() / 3.0)


class FakeOpenMeteo:
    """Stands in for Open-Meteo: deterministic weather for any date, counts the calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        self.calls.append((url, params))
        if "start_date" in params:
            a, b = date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])
            days = [a + timedelta(days=i) for i in range((b - a).days + 1)]
        else:
            past, ahead = int(params["past_days"]), int(params["forecast_days"])
            days = [TODAY + timedelta(days=i) for i in range(-past, ahead)]
        return {
            "daily": {
                "time": [d.isoformat() for d in days],
                "temperature_2m_max": [temp_on(d) for d in days],
                "temperature_2m_min": [temp_on(d) - 8 for d in days],
                "precipitation_sum": [0.0 for _ in days],
            }
        }


def dates(n: int, end: date = date(2026, 10, 25)) -> list[date]:
    return [end - timedelta(days=n - 1 - i) for i in range(n)]


def test_archive_is_fetched_once_then_served_from_the_cache(db_session_factory) -> None:
    fake = FakeOpenMeteo()
    with db_session_factory() as db:
        cov, info = weather.covariates(db, 18.52, 73.86, dates(60), 14, today=TODAY, fetch=fake)
        assert cov is not None
        assert len(cov["temp_max"]) == 74  # history plus forecast days
        assert info["missing_share"] == 0.0
        archive_first = sum("archive" in c[0] for c in fake.calls)
        weather.covariates(db, 18.52, 73.86, dates(60), 14, today=TODAY, fetch=fake)
        archive_after = sum("archive" in c[0] for c in fake.calls)
        assert archive_first == archive_after == 1  # settled days are never fetched twice
        assert db.scalar(select(func.count()).select_from(WeatherDaily)) >= 74
    assert fake.calls[0][1]["latitude"] == "18.5200"
    assert "apikey" not in fake.calls[0][1]  # the free tier sends no key


def test_recent_and_future_days_come_from_the_forecast_api_and_refresh(db_session_factory) -> None:
    fake = FakeOpenMeteo()
    with db_session_factory() as db:
        end = TODAY - timedelta(days=2)  # newer than the archive lag
        weather.covariates(db, 18.52, 73.86, dates(30, end), 14, today=TODAY, fetch=fake)
        urls = [c[0] for c in fake.calls]
        assert any("api.open-meteo.com/v1/forecast" in u for u in urls)
        before = len(fake.calls)
        weather.covariates(db, 18.52, 73.86, dates(30, end), 14, today=TODAY, fetch=fake)
        assert len(fake.calls) > before  # forecasts are refreshed every run


def test_a_failing_service_gives_no_weather_instead_of_an_error(db_session_factory) -> None:
    def boom(url: str, params: dict[str, str]) -> dict[str, Any]:
        raise TimeoutError("service down")

    with db_session_factory() as db:
        cov, info = weather.covariates(db, 18.52, 73.86, dates(60), 14, today=TODAY, fetch=boom)
    assert cov is None
    assert "could not be reached" in info["error"]


def test_too_many_gaps_means_no_weather(db_session_factory) -> None:
    class Sparse(FakeOpenMeteo):
        def __call__(self, url: str, params: dict[str, str]) -> dict[str, Any]:
            out = super().__call__(url, params)
            out["daily"]["temperature_2m_max"] = [None] * len(out["daily"]["time"])
            return out

    with db_session_factory() as db:
        cov, info = weather.covariates(db, 18.52, 73.86, dates(60), 14, today=TODAY, fetch=Sparse())
    assert cov is None
    assert "missing" in info["error"]


def test_paid_key_switches_host_and_sends_the_key(db_session_factory, monkeypatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.get_settings(), "open_meteo_api_key", "secret-key")
    fake = FakeOpenMeteo()
    with db_session_factory() as db:
        weather.covariates(db, 18.52, 73.86, dates(20), 14, today=TODAY, fetch=fake)
    assert fake.calls[0][0].startswith("https://customer-")
    assert fake.calls[0][1]["apikey"] == "secret-key"


def test_production_refuses_the_free_tier_without_a_key() -> None:
    prod = {
        "app_env": "production",
        "jwt_secret_key": "x" * 40,
        "database_url": "postgresql://u:p@h/d",
        "cors_origins": ["https://app.example.in"],
        "app_url": "https://app.example.in",
    }
    assert Settings(**prod).weather_allowed is False  # type: ignore[arg-type]
    assert Settings(**prod, open_meteo_api_key="k").weather_allowed is True  # type: ignore[arg-type]
    assert Settings(weather_enabled=False).weather_allowed is False


# ---------------------------------------------------------------- API


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "wx@shop.in", shop_csv(84))


def wurl(shop, path: str) -> str:
    return f"/api/v1/workspaces/{shop[1]}/weather{path}"


def test_cities_and_setting_a_location(client: TestClient, shop) -> None:
    h = shop[0]
    cities = client.get(wurl(shop, "/cities"), headers=h).json()
    assert any(c["name"] == "Pune" for c in cities)
    st = client.get(wurl(shop, "/status"), headers=h).json()
    assert st["city"] is None
    assert st["free_tier"] is True
    assert "Open-Meteo" in st["attribution"]
    r = client.put(wurl(shop, "/location"), json={"city": "pune"}, headers=h).json()
    assert r["city"] == "Pune"
    assert round(r["latitude"], 2) == 18.52


def test_bad_locations_are_rejected(client: TestClient, shop, make_user) -> None:
    h = shop[0]
    assert (
        client.put(wurl(shop, "/location"), json={"city": "Atlantis"}, headers=h).status_code == 422
    )
    assert client.put(wurl(shop, "/location"), json={}, headers=h).status_code == 422
    assert (
        client.put(
            wurl(shop, "/location"), json={"latitude": 200, "longitude": 10}, headers=h
        ).status_code
        == 422
    )
    stranger = make_user("s@x.in", "S")
    assert (
        client.put(wurl(shop, "/location"), json={"city": "Pune"}, headers=stranger).status_code
        == 404
    )


def test_forecast_uses_weather_when_a_location_is_set(
    client: TestClient, shop, monkeypatch
) -> None:
    fake = FakeOpenMeteo()
    monkeypatch.setattr(weather, "http_fetch", fake)
    client.put(wurl(shop, "/location"), json={"city": "Pune"}, headers=shop[0])
    run_forecast(client, shop)
    r = client.get(f"/api/v1/workspaces/{shop[1]}/forecasts/latest", headers=shop[0]).json()
    w = r["signals"]["weather"]
    assert w["status"] == "ok"
    assert w["city"] == "Pune"
    assert "Open-Meteo" in w["attribution"]
    groups = {g["group"]: g for g in r["accuracy"]["covariates"]["groups"]}  # the backtest decided
    assert groups["weather"]["names"] == ["rain_mm", "temp_max"]
    assert groups["weather"]["used"] == w["used"]
    assert "events" in groups  # festivals and cricket were tested too, separately
    assert fake.calls


def test_forecast_still_works_when_weather_is_down(client: TestClient, shop, monkeypatch) -> None:
    def boom(url: str, params: dict[str, str]) -> dict[str, Any]:
        raise TimeoutError("down")

    monkeypatch.setattr(weather, "http_fetch", boom)
    client.put(wurl(shop, "/location"), json={"city": "Pune"}, headers=shop[0])
    run_forecast(client, shop)
    r = client.get(f"/api/v1/workspaces/{shop[1]}/forecasts/latest", headers=shop[0]).json()
    assert r["signals"]["weather"]["status"] == "unavailable"
    assert any("Weather could not be loaded" in x for x in r["warnings"])


def test_without_a_location_no_weather_call_is_made(client: TestClient, shop, monkeypatch) -> None:
    fake = FakeOpenMeteo()
    monkeypatch.setattr(weather, "http_fetch", fake)
    run_forecast(client, shop)
    r = client.get(f"/api/v1/workspaces/{shop[1]}/forecasts/latest", headers=shop[0]).json()
    assert r["signals"]["weather"]["status"] == "no_location"
    assert fake.calls == []
