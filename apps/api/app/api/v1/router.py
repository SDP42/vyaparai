from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    campaigns,
    costs,
    datasets,
    digests,
    forecasts,
    health,
    intelligence,
    weather,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(datasets.router)
api_router.include_router(analytics.router)
api_router.include_router(intelligence.router)
api_router.include_router(forecasts.router)
api_router.include_router(campaigns.router)
api_router.include_router(costs.router)
api_router.include_router(digests.router)
api_router.include_router(weather.router)
