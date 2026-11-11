from fastapi import APIRouter, Depends

from app.api.deps import require_capability
from app.api.v1.endpoints import (
    agents,
    alerts,
    analytics,
    assistant,
    auth,
    bills,
    campaign_runs,
    campaigns,
    costs,
    datasets,
    digests,
    documents,
    events,
    forecasts,
    goals,
    health,
    intelligence,
    inventory,
    pricing,
    recommendations,
    reports,
    reviews,
    sources,
    stores,
    udhaar,
    weather,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(goals.router)
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(assistant.router)
api_router.include_router(bills.router, dependencies=[Depends(require_capability("supplier"))])
api_router.include_router(documents.router)
api_router.include_router(recommendations.router)
api_router.include_router(pricing.router, dependencies=[Depends(require_capability("margin"))])
api_router.include_router(reports.router, dependencies=[Depends(require_capability("reports"))])
api_router.include_router(reviews.router)
api_router.include_router(stores.router)
api_router.include_router(udhaar.router, dependencies=[Depends(require_capability("credit"))])
api_router.include_router(workspaces.router)
api_router.include_router(workspaces.join_router)
api_router.include_router(datasets.router)
api_router.include_router(analytics.router)
api_router.include_router(agents.router)
api_router.include_router(alerts.router)
api_router.include_router(intelligence.router)
api_router.include_router(forecasts.router)
api_router.include_router(sources.router)
api_router.include_router(events.router)
api_router.include_router(inventory.router)
api_router.include_router(campaigns.router)
api_router.include_router(campaign_runs.router)
api_router.include_router(costs.router, dependencies=[Depends(require_capability("margin"))])
api_router.include_router(digests.router)
api_router.include_router(weather.router)
