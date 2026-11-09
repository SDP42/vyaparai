"""Shared weather cache. Weather is public data: rows are keyed by place and day, not tenant."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class WeatherDaily(Base):
    __tablename__ = "weather_daily"

    # location rounded to 0.1 degree (about 11 km), so nearby shops share rows
    lat_key: Mapped[float] = mapped_column(Float, primary_key=True)
    lon_key: Mapped[float] = mapped_column(Float, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    temp_max: Mapped[float | None] = mapped_column(Float)
    temp_min: Mapped[float | None] = mapped_column(Float)
    rain_mm: Mapped[float | None] = mapped_column(Float)
    kind: Mapped[str] = mapped_column(String(10))  # "actual" (archive) or "forecast"
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
