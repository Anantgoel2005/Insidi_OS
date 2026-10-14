from __future__ import annotations

import logging
import asyncio
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.endpoints import public
from app.api.dependencies import csrf_tokens_match
from app.config import settings
from app.core.database import engine
from app.core.rate_limit import rate_limiter
from app.services.live_demo import run_scheduler

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("insidi-os")


async def lifespan(app: FastAPI):
    settings.validate_runtime()
    scheduler = asyncio.create_task(run_scheduler())
    try:
        yield
    finally:
        scheduler.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler
        await engine.dispose()


app = FastAPI(
    title="Insidi_OS",
    description="Identity-aware insider-threat detection, live attack walkthroughs and synthetic sandbox response",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    if request.url.path == "/api/v1/auth/login" and request.method == "POST":
        if not rate_limiter.allowed(f"login:{client_ip}", limit=10, seconds=300):
            return JSONResponse(status_code=429, content={"detail": "Too many login attempts"})
    if request.url.path.startswith("/c/") and request.method == "GET":
        if not rate_limiter.allowed(f"canary:{client_ip}", limit=60, seconds=60):
            return JSONResponse(status_code=429, content={"detail": "Too many callback requests"})
    mutation = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    cookie_authenticated = bool(request.cookies.get("access_token")) and not request.headers.get("authorization")
    if mutation and cookie_authenticated and request.url.path.startswith("/api/v1/") and request.url.path != "/api/v1/auth/login":
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_tokens_match(csrf_cookie, csrf_header):
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if settings.deployment_mode == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

app.include_router(api_router, prefix="/api/v1")
app.include_router(public.router)


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"})
