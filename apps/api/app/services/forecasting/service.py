"""Start forecast jobs, run them in the background and read stored results."""

import csv
import io
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.dataset import Job, JobStatus, JobType
from app.models.forecast import ForecastRun, ForecastSeries
from app.models.user import User
from app.models.workspace import Workspace
from app.services import audit
from app.services.analytics import queries as q
from app.services.forecasting import engine
from app.services.forecasting.panel import load_panel

KEEP_RUNS = 5
STALE_JOB_MINUTES = 15  # a job that never finished (server restarted) must not block new runs
SORTS = {
    "units_next": lambda r: r.units_next,
    "change": lambda r: _change(r) if _change(r) is not None else -1e9,
    "wape": lambda r: r.backtest_wape if r.backtest_wape is not None else 1e9,
    "name": lambda r: r.name.lower(),
}


class NotEnoughDataError(AppError):
    status_code = 422
    code = "not_enough_data"


def _change(r: ForecastSeries) -> float | None:
    if r.units_last < 5:  # tiny bases make percentage changes meaningless
        return None
    return round((r.units_next - r.units_last) / r.units_last * 100, 1)


def status_for(db: Session, ws: uuid.UUID) -> dict[str, Any]:
    first, last = q.workspace_bounds(db, ws)
    days = ((last - first).days + 1) if first and last else 0
    ok = days >= engine.MIN_DAYS_FORECAST
    return {
        "can_forecast": ok,
        "reason": None
        if ok
        else f"Needs at least {engine.MIN_DAYS_FORECAST} days of sales; there are {days}.",
        "latest_data_date": last,
        "history_days": days,
    }


def start_forecast(db: Session, workspace: Workspace, user: User) -> Job:
    st = status_for(db, workspace.id)
    if not st["can_forecast"]:
        raise NotEnoughDataError(st["reason"])
    running = db.scalars(
        select(Job).where(
            Job.workspace_id == workspace.id,
            Job.job_type == JobType.FORECAST_TRAINING,
            Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
    ).first()
    if running is not None:
        age = datetime.now(UTC) - running.created_at.replace(
            tzinfo=running.created_at.tzinfo or UTC
        )
        if age < timedelta(minutes=STALE_JOB_MINUTES):
            return running
        running.status = JobStatus.FAILED
        running.error_message = "The server restarted before this forecast finished."
        running.finished_at = datetime.now(UTC)
    job = Job(
        workspace_id=workspace.id,
        job_type=JobType.FORECAST_TRAINING,
        status=JobStatus.QUEUED,
        created_by_id=user.id,
    )
    db.add(job)
    audit.record(
        db,
        action="forecast.started",
        actor_user_id=user.id,
        workspace_id=workspace.id,
        entity_type="job",
        entity_id=job.id,
    )
    db.commit()
    return job


def run_forecast_job(engine_: Engine, job_id: uuid.UUID) -> None:
    """Background task: build the panel, run the engine, store the results."""
    with Session(bind=engine_, expire_on_commit=False) as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.progress = 10
        db.commit()
        try:
            panel = load_panel(db, job.workspace_id)
            if panel is None:
                raise NotEnoughDataError("No completed sales to forecast from")
            job.progress = 30
            db.commit()
            result = engine.run(panel)
            if result is None:
                raise NotEnoughDataError("Not enough days of sales to forecast")
            job.progress = 85
            db.commit()
            run = ForecastRun(
                workspace_id=job.workspace_id,
                job_id=job.id,
                as_of=result.as_of,
                horizon=result.horizon,
                history_days=result.history_days,
                n_series=result.n_series,
                seconds=result.seconds,
                summary=result.summary,
                created_by_id=job.created_by_id,
            )
            db.add(run)
            db.flush()
            db.add_all(
                ForecastSeries(
                    workspace_id=job.workspace_id,
                    run_id=run.id,
                    sku=s.sku,
                    name=s.name,
                    category=s.category,
                    model=s.model,
                    pattern=s.pattern,
                    confidence=s.confidence,
                    backtest_wape=s.backtest_wape,
                    backtest_bias=s.backtest_bias,
                    units_last=s.units_last,
                    units_next=s.units_next,
                    units_next_low=s.units_next_low,
                    units_next_high=s.units_next_high,
                    net_per_unit=s.net_per_unit,
                    data=s.data,
                )
                for s in result.series
            )
            _prune(db, job.workspace_id)
            job.status = JobStatus.SUCCEEDED
            job.progress = 100
            job.result = {
                "run_id": str(run.id),
                "series": result.n_series,
                "seconds": result.seconds,
                "wape": result.summary["accuracy"].get("wape"),
            }
        except Exception as exc:
            db.rollback()
            job = db.get(Job, job_id)
            if job is not None:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)[:500]
        finally:
            if job is not None:
                job.finished_at = datetime.now(UTC)
            db.commit()


def _prune(db: Session, ws: uuid.UUID) -> None:
    old = db.scalars(
        select(ForecastRun.id)
        .where(ForecastRun.workspace_id == ws)
        .order_by(ForecastRun.created_at.desc())
        .offset(KEEP_RUNS)
    ).all()
    if old:
        db.execute(delete(ForecastSeries).where(ForecastSeries.run_id.in_(old)))
        db.execute(delete(ForecastRun).where(ForecastRun.id.in_(old)))


def latest_run(db: Session, ws: uuid.UUID) -> ForecastRun | None:
    return db.scalars(
        select(ForecastRun)
        .where(ForecastRun.workspace_id == ws)
        .order_by(ForecastRun.created_at.desc())
        .limit(1)
    ).first()


def _mover(r: ForecastSeries) -> dict[str, Any]:
    return {
        "sku": r.sku,
        "name": r.name,
        "units_last": round(r.units_last, 1),
        "units_next": round(r.units_next, 1),
        "change_pct": _change(r) or 0.0,
    }


def overview(db: Session, workspace: Workspace, run: ForecastRun) -> dict[str, Any]:
    rows = db.scalars(select(ForecastSeries).where(ForecastSeries.run_id == run.id)).all()
    s = run.summary
    fc = s["totals"]["forecast"]
    units_next = sum(d["p50"] for d in fc)
    low, high = sum(d["p10"] for d in fc), sum(d["p90"] for d in fc)
    last_units = sum(r.units_last for r in rows)
    net_next = sum(d["net"] for d in fc)
    net_last = sum(r.units_last * (r.net_per_unit or 0.0) for r in rows)

    def pct(a: float, b: float) -> float | None:
        return round((a - b) / b * 100, 1) if b > 0 else None

    movers = sorted((r for r in rows if _change(r) is not None), key=lambda r: _change(r) or 0)
    _, last_date = q.workspace_bounds(db, workspace.id)
    return {
        "run": run,
        "currency": workspace.currency,
        "stale": bool(last_date and last_date > run.as_of),
        "latest_data_date": last_date,
        "kpis": {
            "units_next": round(units_next, 1),
            "units_next_low": round(low, 1),
            "units_next_high": round(high, 1),
            "units_last": round(last_units, 1),
            "units_change_pct": pct(units_next, last_units),
            "net_next": round(net_next, 2),
            "net_last_est": round(net_last, 2),
            "net_change_pct": pct(net_next, net_last),
        },
        "totals": s["totals"],
        "accuracy": s["accuracy"],
        "model_card": s["model_card"],
        "risers": [_mover(r) for r in reversed(movers[-5:]) if (_change(r) or 0) > 0],
        "fallers": [_mover(r) for r in movers[:5] if (_change(r) or 0) < 0],
        "confidence_counts": {
            c: sum(1 for r in rows if r.confidence == c) for c in ("high", "medium", "low")
        },
        "warnings": s["warnings"],
    }


def _row(r: ForecastSeries) -> dict[str, Any]:
    d = r.data
    spark = [*d["hist"][-28:], *d["p50"]]
    return {
        "sku": r.sku,
        "name": r.name,
        "category": r.category,
        "model": r.model,
        "pattern": r.pattern,
        "confidence": r.confidence,
        "backtest_wape": r.backtest_wape,
        "backtest_bias": r.backtest_bias,
        "units_last": round(r.units_last, 1),
        "units_next": round(r.units_next, 1),
        "units_next_low": round(r.units_next_low, 1),
        "units_next_high": round(r.units_next_high, 1),
        "change_pct": _change(r),
        "spark": spark,
    }


def products_page(
    db: Session,
    run: ForecastRun,
    *,
    search: str | None,
    confidence: str | None,
    model: str | None,
    pattern: str | None,
    sort: str,
    descending: bool,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    stmt = select(ForecastSeries).where(ForecastSeries.run_id == run.id)
    if confidence:
        stmt = stmt.where(ForecastSeries.confidence == confidence)
    if model:
        stmt = stmt.where(ForecastSeries.model == model)
    if pattern:
        stmt = stmt.where(ForecastSeries.pattern == pattern)
    if search and search.strip():
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(ForecastSeries.name).like(like) | func.lower(ForecastSeries.sku).like(like)
        )
    rows = list(db.scalars(stmt).all())
    rows.sort(key=SORTS.get(sort, SORTS["units_next"]), reverse=descending)
    return {
        "run_id": run.id,
        "horizon": run.horizon,
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "items": [_row(r) for r in rows[offset : offset + limit]],
    }


def product_detail(db: Session, run: ForecastRun, sku: str) -> dict[str, Any]:
    r = db.scalars(
        select(ForecastSeries).where(ForecastSeries.run_id == run.id, ForecastSeries.sku == sku)
    ).first()
    if r is None:
        raise NotFoundError("No forecast for this product")
    return {**_row(r), "data": r.data, "net_per_unit": r.net_per_unit}


def export_csv(db: Session, run: ForecastRun) -> Iterator[str]:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["sku", "product", "category", "date", "p10", "p50", "p90", "model", "confidence"])
    yield buf.getvalue()
    rows = db.scalars(
        select(ForecastSeries).where(ForecastSeries.run_id == run.id).order_by(ForecastSeries.sku)
    )
    for r in rows:
        d = r.data
        start = date.fromisoformat(d["fc_start"])
        for k in range(len(d["p50"])):
            buf.seek(0)
            buf.truncate()
            w.writerow([r.sku, r.name, r.category or "", (start + timedelta(days=k)).isoformat(),
                        d["p10"][k], d["p50"][k], d["p90"][k], r.model, r.confidence])  # fmt: skip
            yield buf.getvalue()
