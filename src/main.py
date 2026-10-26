"""
FastAPI Application Entrypoint & Lifespan Management.
Automated PayPal Dispute Resolution Engine.
"""

import logging
import os
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from src.api.v1 import api_v1_router
from src.core.config import get_settings
from src.core.exceptions import (
    DisputeNotFoundError,
    PayPalAPIError,
    PayPalDisputeEngineException,
    WebhookVerificationError,
)

# Configure structured logging
settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("dispute_engine")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context:
    Initializes required storage directories, warmups, and teardown.
    """
    logger.info("Initializing PayPal Dispute Resolution Engine...")
    os.makedirs(os.path.join(os.getcwd(), "artifacts", "dossiers"), exist_ok=True)
    yield
    logger.info("Shutting down PayPal Dispute Resolution Engine.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise-grade automated dispute resolution, AI arbitration, and evidence compiler for PayPal.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Injects or propagates correlation IDs across HTTP request/response lifecycles.
    """
    correlation_id = request.headers.get("X-Correlation-Id") or f"CORR-{uuid.uuid4().hex[:12]}"
    start_time = time.time()

    # Store in request state
    request.state.correlation_id = correlation_id

    response: Response = await call_next(request)

    duration = (time.time() - start_time) * 1000
    response.headers["X-Correlation-Id"] = correlation_id
    response.headers["X-Process-Time-Ms"] = f"{duration:.2f}"
    return response


# Global Exception Handlers
@app.exception_handler(WebhookVerificationError)
async def webhook_verification_exception_handler(request: Request, exc: WebhookVerificationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "WebhookVerificationError",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(DisputeNotFoundError)
async def dispute_not_found_exception_handler(request: Request, exc: DisputeNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "DisputeNotFoundError", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(PayPalAPIError)
async def paypal_api_exception_handler(request: Request, exc: PayPalAPIError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "PayPalAPIError",
            "message": exc.message,
            "status_code": exc.status_code,
            "response_body": exc.response_body,
        },
    )


@app.exception_handler(PayPalDisputeEngineException)
async def general_domain_exception_handler(request: Request, exc: PayPalDisputeEngineException):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": exc.__class__.__name__, "message": exc.message, "details": exc.details},
    )


# Health check & Root
@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Liveness & readiness probe."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "paypal_mode": settings.PAYPAL_MODE,
    }


# Static Files Directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

ASSETS_DIR = os.path.join(STATIC_DIR, "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/", tags=["System"])
@app.get("/login", tags=["System"])
@app.get("/auth", tags=["System"])
@app.get("/dashboard", tags=["System"])
async def root(request: Request):
    """
    Root Web Entrypoint:
    Serves the LexiShield Web Application if accessed via browser,
    or JSON metadata if requested via API client.
    """
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/html" not in accept_header:
        return {
            "message": "PayPal Automated Dispute Resolution Engine is active.",
            "docs": "/docs",
            "api_v1": settings.API_V1_STR,
        }

    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")

    return {
        "message": "PayPal Automated Dispute Resolution Engine is active.",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }


# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
