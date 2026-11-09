"""Shop location and weather status. Weather feeds the forecast only when it helps (backtest)."""

from fastapi import APIRouter

from app.api.deps import AdminCtx, DbSession, ViewerCtx
from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.weather import City, LocationIn, WeatherStatus
from app.services import audit, weather

router = APIRouter(prefix="/workspaces/{workspace_id}/weather", tags=["weather"])


class UnknownCityError(AppError):
    status_code = 422
    code = "unknown_city"


def _status(ws: object) -> WeatherStatus:
    st = get_settings()
    note = None
    if not st.weather_enabled:
        note = "Weather is switched off on this server."
    elif not st.weather_allowed:
        note = "The free weather service is for non-commercial use; production needs a paid key."
    return WeatherStatus(
        enabled=st.weather_allowed,
        free_tier=not st.open_meteo_api_key,
        city=getattr(ws, "city", None),
        latitude=getattr(ws, "latitude", None),
        longitude=getattr(ws, "longitude", None),
        attribution=weather.ATTRIBUTION,
        note=note,
    )


@router.get("/cities", response_model=list[City])
def cities(ctx: ViewerCtx) -> list[City]:
    return [City(name=n, state=s, latitude=la, longitude=lo) for n, s, la, lo in weather.CITIES]


@router.get("/status", response_model=WeatherStatus)
def status(ctx: ViewerCtx) -> WeatherStatus:
    return _status(ctx.workspace)


@router.put("/location", response_model=WeatherStatus)
def set_location(data: LocationIn, ctx: AdminCtx, db: DbSession) -> WeatherStatus:
    ws = ctx.workspace
    if data.latitude is not None and data.longitude is not None:
        ws.latitude, ws.longitude, ws.city = data.latitude, data.longitude, data.city
    else:
        found = weather.find_city(data.city or "")
        if found is None:
            raise UnknownCityError("Pick a city from the list, or give coordinates")
        ws.city, ws.latitude, ws.longitude, ws.state = found[0], found[2], found[3], found[1]
    audit.record(
        db,
        action="workspace.location_set",
        actor_user_id=ctx.user.id,
        workspace_id=ws.id,
        entity_type="workspace",
        entity_id=ws.id,
    )
    db.commit()
    return _status(ws)
