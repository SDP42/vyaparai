from fastapi import APIRouter

from app.api.v1.endpoints import (
    alerts,
    analytics,
    assistant,
    auth,
    bills,
    campaigns,
    costs,
    datasets,
    digests,
    documents,
    events,
    forecasts,
    health,
    intelligence,
    inventory,
    reviews,
    sources,
    weather,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(assistant.router)
api_router.include_router(bills.router)
api_router.include_router(documents.router)
api_router.include_router(reviews.router)
api_router.include_router(workspaces.router)
api_router.include_router(workspaces.join_router)
api_router.include_router(datasets.router)
api_router.include_router(analytics.router)
api_router.include_router(alerts.router)
api_router.include_router(intelligence.router)
api_router.include_router(forecasts.router)
api_router.include_router(sources.router)
api_router.include_router(events.router)
api_router.include_router(inventory.router)
api_router.include_router(campaigns.router)
api_router.include_router(costs.router)
api_router.include_router(digests.router)
api_router.include_router(weather.router)
