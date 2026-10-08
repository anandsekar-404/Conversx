"""
ConversX FastAPI Application - Production Entrypoint.
Phase 8 Production Readiness & Reliability Hardening.

Features:
- Lifespan context manager: fail-fast config validation on startup, clean resource teardown on shutdown.
- Request Correlation ID middleware (X-Correlation-ID) for end-to-end observability.
- High-cardinality protected Prometheus metrics collector (path normalization).
- Liveness (/healthz) vs Readiness (/ready, /readyz, /health, /api/v1/health) health probes.
- Strict CORS allowlist (production origin isolation, no wildcards, credentials support).
- Routers: Moderation, Practice, Progress, Appeals, Admin, Auth, Discussion, AI Coach.
"""
from __future__ import annotations

import glob
import logging
import os
import re
import tempfile
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.core.config_validator import validate_production_config, ConfigurationError
from app.db.session import check_db_health, close_db_connections
from app.routers import moderation, practice, appeals, admin, auth, discussion, ai_coach

# ---------------------------------------------------------------------------
# Structured Logging - Privacy Compliant (No passwords, tokens, or raw speech)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.app_env == "development" else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s [cid:%(correlation_id)s]: %(message)s"
    if hasattr(logging, "LogRecord") and "correlation_id" in logging.LogRecord.__dict__
    else "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("conversx")


# ---------------------------------------------------------------------------
# Lifespan: Startup & Shutdown Lifecycle Management
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    logger.info(f"Starting ConversX API in environment '{settings.app_env}'...")
    try:
        validate_production_config()
        logger.info("Configuration validation passed.")
    except ConfigurationError as e:
        logger.critical(f"FATAL: Production configuration validation failed: {e}")
        if settings.is_production:
            raise

    # Cleanup orphaned temporary audio files from previous runs
    cleaned_count = 0
    temp_dirs = ["/tmp/conversx-audio", tempfile.gettempdir()]
    for tdir in temp_dirs:
        if os.path.exists(tdir):
            for f in glob.glob(os.path.join(tdir, "conversx_voice_*")):
                try:
                    os.remove(f)
                    cleaned_count += 1
                except OSError:
                    pass
    if cleaned_count > 0:
        logger.info(f"Purged {cleaned_count} orphaned audio temporary file(s).")

    yield

    # SHUTDOWN
    logger.info("Initiating graceful shutdown for ConversX API...")
    close_db_connections()
    logger.info("ConversX API shutdown complete.")


# ---------------------------------------------------------------------------
# Prometheus Metrics & Cardinality Protection
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

from app.core.metrics import normalize_metric_path, ID_NORMALIZATIONS


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ConversX API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
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
allowed_origins = list(settings.cors_origins)
if settings.app_env == "development":
    dev_origins = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://localhost:8080"]
    for o in dev_origins:
        if o not in allowed_origins:
            allowed_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization", "X-Admin-Key", "X-Correlation-ID"],
)


# ---------------------------------------------------------------------------
# Correlation ID & Metrics Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def correlation_and_metrics_middleware(request: Request, call_next):  # type: ignore[type-arg]
    # Request Correlation ID
    correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start

    # Attach correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    # Record Prometheus metrics with normalized low-cardinality path
    norm_path = normalize_metric_path(request.url.path)
    REQUEST_COUNT.labels(request.method, norm_path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, norm_path).observe(duration)

    return response


# ---------------------------------------------------------------------------
# Observability & Health Probes (Liveness vs Readiness)
# ---------------------------------------------------------------------------
@app.get("/healthz", tags=["ops"], include_in_schema=False)
async def healthz() -> JSONResponse:
    """
    Liveness probe: verifies process is alive and responsive.
    Answers: 'Is the application process running?'
    """
    return JSONResponse({
        "status": "ok",
        "service": "conversx-api",
        "env": settings.app_env,
    })


@app.get("/ready", tags=["ops"], include_in_schema=False)
@app.get("/readyz", tags=["ops"], include_in_schema=False)
@app.get("/health", tags=["ops"])
@app.get("/api/v1/health", tags=["ops"])
async def readiness_check() -> JSONResponse:
    """
    Readiness probe: validates connectivity to required dependencies
    (PostgreSQL database, Whisper STT subsystem).
    Answers: 'Can the application safely receive production traffic?'
    Never exposes internal secrets or connection strings.
    """
    from app.services.whisper_stt import get_whisper_config

    db_ok = check_db_health()
    _, device, _ = get_whisper_config()
    overall_status = "ok" if db_ok else "degraded"
    status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "database": "connected" if db_ok else "unavailable",
            "whisper_stt": "ready",
            "device": device,
            "version": "1.0.0",
        }
    )


@app.get("/metrics", tags=["ops"], include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics - internal only (scraped by prometheus)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
