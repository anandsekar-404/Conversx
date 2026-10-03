"""
ConversX FastAPI application — main entrypoint (Week 1 skeleton).
Full auth, routing and middleware are added in Week 2+.
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings

# ---------------------------------------------------------------------------
# Logging — structured JSON in production, plain text in development
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.app_env == "development" else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("conversx")

# ---------------------------------------------------------------------------
# Prometheus metrics
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
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ConversX API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.app_env != "production" else None,
)

# CORS — allowlist only; no wildcards (§7)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
)


# ---------------------------------------------------------------------------
# Middleware — request latency + structured logging
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):  # type: ignore[type-arg]
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start
    path = request.url.path
    REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(duration)
    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        },
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/healthz", tags=["ops"], include_in_schema=False)
async def healthz() -> JSONResponse:
    """Health check used by Docker, deploy.sh and Uptime Kuma."""
    return JSONResponse({"status": "ok", "env": settings.app_env})


@app.get("/metrics", tags=["ops"], include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics — internal only (not exposed via Tunnel)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/hello", tags=["week1"])
async def hello() -> JSONResponse:
    """Week 1 smoke-test endpoint. Removed or secured in Week 2."""
    return JSONResponse({"message": "ConversX API is running", "version": "0.1.0"})
