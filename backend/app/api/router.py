from __future__ import annotations

from fastapi import APIRouter

from app.api.endpoints import (
    alerts,
    auth,
    canaries,
    dashboard,
    demo,
    engagement,
    events,
    honeypots,
    investigations,
    live_demo,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(honeypots.router, prefix="/honeypots", tags=["Honeypots"])
api_router.include_router(canaries.router, prefix="/canaries", tags=["Canaries"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(engagement.router, prefix="/engagement", tags=["Engagement"])
api_router.include_router(demo.router, prefix="/demo", tags=["Live Showcase"])
api_router.include_router(live_demo.router, prefix="/demo/live", tags=["Live Showcase"])
api_router.include_router(investigations.router, prefix="/investigations", tags=["Investigations"])
