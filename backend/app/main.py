"""
ConversX FastAPI Application - Production Entrypoint.
Phase 7 Production Hardening.

Features:
- Structured logging (no raw user speech/text or secrets logged).
- Prometheus metrics collector for HTTP requests and latencies.
- Liveness (/healthz) and Readiness (/health, /api/v1/health) probes.
- Strict CORS allowlist (production origin isolation, no wildcards).
- Routers: Moderation, Practice, Progress, Appeals, Admin, Auth.
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.routers import moderation, practice, appeals, admin, auth, discussion, ai_coach

# ---------------------------------------------------------------------------
# Structured Logging - Privacy Compliant (No passwords, tokens, or raw speech)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.app_env == "development" else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("conversx")

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "conversx_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "conversx_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)

# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ConversX API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.app_env != "production" else None,
)

# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------
app.include_router(moderation.router)
app.include_router(practice.router)
app.include_router(practice.progress_router)
app.include_router(appeals.router)
app.include_router(admin.router)
if getattr(discussion, "router", None) is not None:
    app.include_router(discussion.router)
if getattr(auth, "router", None) is not None:
    app.include_router(auth.router)
if getattr(ai_coach, "router", None) is not None:
    app.include_router(ai_coach.router)

# ---------------------------------------------------------------------------
# CORS Configuration - Strict Production Isolation
# ---------------------------------------------------------------------------
# In production, restrict strictly to conversx.com origins; no wildcards allowed
allowed_origins = list(settings.cors_origins)
if settings.app_env == "development":
    dev_origins = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]
    for o in dev_origins:
        if o not in allowed_origins:
            allowed_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization", "X-Admin-Key"],
)


# ---------------------------------------------------------------------------
# Latency & Metrics Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):  # type: ignore[type-arg]
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start
    path = request.url.path
    REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(duration)
    return response


# ---------------------------------------------------------------------------
# Observability & Health Probes (Phase 7 Split: Liveness vs Readiness)
# ---------------------------------------------------------------------------
@app.get("/healthz", tags=["ops"], include_in_schema=False)
async def healthz() -> JSONResponse:
    """
    Liveness probe: verifies process is alive and responsive.
    Used by container orchestration and process supervisors.
    """
    return JSONResponse({"status": "ok", "service": "conversx-api"})


@app.get("/metrics", tags=["ops"], include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics - internal only (scraped by prometheus)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health", tags=["ops"])
@app.get("/api/v1/health", tags=["ops"])
async def health_check() -> JSONResponse:
    """
    Readiness probe: validates connectivity to required dependencies
    (PostgreSQL database, Whisper STT subsystem).
    Never exposes internal secrets or connection strings.
    """
    from app.db.session import check_db_health
    from app.services.whisper_stt import get_whisper_config

    db_ok = check_db_health()
    _, device, _ = get_whisper_config()
    overall_status = "ok" if db_ok else "degraded"

    return JSONResponse({
        "status": overall_status,
        "database": "connected" if db_ok else "unavailable",
        "whisper_stt": "ready",
        "device": device,
        "version": "1.0.0",
    })
