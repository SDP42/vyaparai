"""Daily weather for a shop's location, cached, from Open-Meteo.

Licence (docs/research/EXTERNAL-FACTORS.md): the free endpoint is for non-commercial use only, so
``Settings.weather_allowed`` blocks it in production unless ``OPEN_METEO_API_KEY`` is set. Data is
CC BY 4.0, so the UI shows the attribution. Only coordinates are sent, never customer data.
The paid-endpoint host names below follow Open-Meteo's pricing page; confirm them with the key.
"""

import json
import logging
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.weather import WeatherDaily

log = logging.getLogger("app.weather")
Arr = NDArray[np.float64]
Fetcher = Callable[[str, dict[str, str]], dict[str, Any]]

ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
ARCHIVE_LAG_DAYS = (
    6  # the archive trails real time by a few days; newer days come from the forecast API
)
DAILY = "temperature_2m_max,temperature_2m_min,precipitation_sum"
MAX_MISSING_SHARE = 0.2  # more gaps than this and the signal is not trustworthy

CITIES: list[tuple[str, str, float, float]] = [
    ("Agra", "Uttar Pradesh", 27.18, 78.02), ("Ahmedabad", "Gujarat", 23.02, 72.57),
    ("Amritsar", "Punjab", 31.63, 74.87), ("Bengaluru", "Karnataka", 12.97, 77.59),
    ("Bhopal", "Madhya Pradesh", 23.26, 77.41), ("Bhubaneswar", "Odisha", 20.30, 85.82),
    ("Chandigarh", "Chandigarh", 30.73, 76.78), ("Chennai", "Tamil Nadu", 13.08, 80.27),
    ("Coimbatore", "Tamil Nadu", 11.02, 76.96), ("Dehradun", "Uttarakhand", 30.32, 78.03),
    ("Delhi", "Delhi", 28.61, 77.21), ("Goa (Panaji)", "Goa", 15.49, 73.83),
    ("Guwahati", "Assam", 26.14, 91.74), ("Hyderabad", "Telangana", 17.39, 78.49),
    ("Indore", "Madhya Pradesh", 22.72, 75.86), ("Jaipur", "Rajasthan", 26.91, 75.79),
    ("Kanpur", "Uttar Pradesh", 26.45, 80.33), ("Kochi", "Kerala", 9.93, 76.27),
    ("Kolkata", "West Bengal", 22.57, 88.36), ("Lucknow", "Uttar Pradesh", 26.85, 80.95),
    ("Ludhiana", "Punjab", 30.90, 75.86), ("Madurai", "Tamil Nadu", 9.93, 78.12),
    ("Mumbai", "Maharashtra", 19.08, 72.88), ("Mysuru", "Karnataka", 12.30, 76.64),
    ("Nagpur", "Maharashtra", 21.15, 79.09), ("Nashik", "Maharashtra", 19.99, 73.79),
    ("Patna", "Bihar", 25.59, 85.14), ("Pune", "Maharashtra", 18.52, 73.86),
    ("Raipur", "Chhattisgarh", 21.25, 81.63), ("Ranchi", "Jharkhand", 23.34, 85.31),
    ("Surat", "Gujarat", 21.17, 72.83), ("Thane", "Maharashtra", 19.22, 72.98),
    ("Vadodara", "Gujarat", 22.31, 73.18), ("Varanasi", "Uttar Pradesh", 25.32, 82.97),
    ("Visakhapatnam", "Andhra Pradesh", 17.69, 83.22),
]  # fmt: skip


def find_city(name: str) -> tuple[str, str, float, float] | None:
    return next((c for c in CITIES if c[0].lower() == name.strip().lower()), None)


def http_fetch(url: str, params: dict[str, str]) -> dict[str, Any]:
    timeout = get_settings().weather_timeout_seconds
    req = urllib.request.Request(  # noqa: S310 - fixed https hosts
        f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "vyapar-ai/0.1"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        data = json.loads(r.read())
    if not isinstance(data, dict):
        raise ValueError("unexpected weather response")
    return data


def _hosts() -> tuple[str, str, dict[str, str]]:
    key = get_settings().open_meteo_api_key
    if key:
        return (
            "https://customer-archive-api.open-meteo.com/v1/archive",
            "https://customer-api.open-meteo.com/v1/forecast",
            {"apikey": key},
        )
    return (
        "https://archive-api.open-meteo.com/v1/archive",
        "https://api.open-meteo.com/v1/forecast",
        {},
    )


def _key(x: float) -> float:
    return round(x, 1)


def _rows(payload: dict[str, Any], kind: str, lat: float, lon: float) -> list[WeatherDaily]:
    d = payload["daily"]
    out = []
    for i, day in enumerate(d["time"]):
        out.append(
            WeatherDaily(
                lat_key=_key(lat),
                lon_key=_key(lon),
                day=date.fromisoformat(day),
                temp_max=d["temperature_2m_max"][i],
                temp_min=d["temperature_2m_min"][i],
                rain_mm=d["precipitation_sum"][i],
                kind=kind,
            )
        )
    return out


def _store(db: Session, rows: list[WeatherDaily]) -> None:
    for r in rows:
        db.merge(r)
    db.commit()


def ensure(
    db: Session, lat: float, lon: float, first: date, last: date, today: date, fetch: Fetcher
) -> None:
    """Fill the cache for first..last: archive for settled days, forecast API for the rest."""
    cached = {
        r.day
        for r in db.scalars(
            select(WeatherDaily).where(
                WeatherDaily.lat_key == _key(lat),
                WeatherDaily.lon_key == _key(lon),
                WeatherDaily.day >= first,
                WeatherDaily.day <= last,
            )
        )
    }
    archive_cut = today - timedelta(days=ARCHIVE_LAG_DAYS)
    arch_url, fc_url, auth = _hosts()
    base = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "daily": DAILY,
        "timezone": "auto",
        **auth,
    }

    missing = [d for d in _days(first, min(last, archive_cut)) if d not in cached]
    if missing:
        payload = fetch(
            arch_url,
            {**base, "start_date": missing[0].isoformat(), "end_date": missing[-1].isoformat()},
        )
        _store(db, _rows(payload, "actual", lat, lon))

    if last > archive_cut:  # recent past and future: always refresh, forecasts change daily
        past = max(0, (today - max(first, archive_cut + timedelta(days=1))).days)
        ahead = max(1, min(16, (last - today).days + 1))
        payload = fetch(
            fc_url, {**base, "past_days": str(min(past, 92)), "forecast_days": str(ahead)}
        )
        _store(db, _rows(payload, "forecast", lat, lon))


def _days(a: date, b: date) -> list[date]:
    return [a + timedelta(days=i) for i in range((b - a).days + 1)] if b >= a else []


def covariates(
    db: Session,
    lat: float,
    lon: float,
    dates: list[date],
    horizon: int,
    *,
    today: date,
    fetch: Fetcher | None = None,
) -> tuple[dict[str, Arr] | None, dict[str, Any]]:
    """Daily temperature and rain covering the history and the forecast period.

    Returns (covariates or None, info). Any failure or too many gaps returns None so the forecast
    runs without weather and says so.
    """
    fetch = fetch or http_fetch
    full = [*dates, *[dates[-1] + timedelta(days=i + 1) for i in range(horizon)]]
    info: dict[str, Any] = {"attribution": ATTRIBUTION, "source": "Open-Meteo"}
    try:
        ensure(db, lat, lon, full[0], full[-1], today, fetch)
    except Exception as exc:  # network, bad payload, rate limit
        log.warning("weather unavailable: %s", exc)
        return None, {**info, "error": "The weather service could not be reached."}
    rows = {
        r.day: r
        for r in db.scalars(
            select(WeatherDaily).where(
                WeatherDaily.lat_key == _key(lat),
                WeatherDaily.lon_key == _key(lon),
                WeatherDaily.day >= full[0],
                WeatherDaily.day <= full[-1],
            )
        )
    }
    tmax = np.array(
        [rows[d].temp_max if d in rows and rows[d].temp_max is not None else np.nan for d in full],
        float,
    )
    rain = np.array(
        [rows[d].rain_mm if d in rows and rows[d].rain_mm is not None else np.nan for d in full],
        float,
    )
    missing = float(np.isnan(tmax).mean())
    if missing > MAX_MISSING_SHARE:
        return None, {**info, "error": f"Weather is missing for {missing:.0%} of days."}
    tmax = _fill(tmax)
    rain = np.nan_to_num(rain, nan=0.0)
    info["forecast_days"] = int(
        sum(1 for d in full[-horizon:] if d in rows and rows[d].kind == "forecast")
    )
    info["missing_share"] = round(missing, 3)
    return {"temp_max": tmax, "rain_mm": rain}, info


def _fill(a: Arr) -> Arr:
    """Fill gaps with the nearest earlier value (or the mean when the series starts empty)."""
    out = a.copy()
    mean = float(np.nanmean(out)) if not np.isnan(out).all() else 0.0
    last = mean
    for i, v in enumerate(out):
        if np.isnan(v):
            out[i] = last
        else:
            last = v
    return out
