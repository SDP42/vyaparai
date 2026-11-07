from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import AppSettings, DbSession

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]
    version: str
    environment: str
    database: Literal["ok", "unavailable"] | None = None


@router.get("/live", response_model=HealthStatus, summary="Liveness probe")
def live(settings: AppSettings) -> HealthStatus:
    return HealthStatus(status="ok", version=settings.app_version, environment=settings.app_env)


@router.get(
    "/ready",
    response_model=HealthStatus,
    summary="Readiness probe (checks database)",
    responses={503: {"model": HealthStatus}},
)
def ready(db: DbSession, settings: AppSettings) -> HealthStatus | JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        body = HealthStatus(
            status="unavailable",
            version=settings.app_version,
            environment=settings.app_env,
            database="unavailable",
        )
        return JSONResponse(status_code=503, content=body.model_dump())
    return HealthStatus(
        status="ok", version=settings.app_version, environment=settings.app_env, database="ok"
    )
