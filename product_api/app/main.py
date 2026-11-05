"""CEI-InOE Product API - application factory.

Private upstream of the FIWARE Data Space Connector. It must never be exposed
publicly; no CORS middleware is installed on purpose (server-to-server only).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.auth import Authenticator, build_authenticator
from app.config import Settings, validate_runtime
from app.repositories.energy_repository import EnergyRepository, PostgresEnergyRepository
from app.routers import health, products
from app.services.audit import (
    RateLimiter,
    configure_audit_logging,
    emit_audit,
    resolve_request_id,
)
from app.services.site_access import SiteRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    registry: SiteRegistry | None = None,
    repository: EnergyRepository | None = None,
    authenticator: Authenticator | None = None,
) -> FastAPI:
    """Build the app. Collaborators may be injected (used by tests)."""
    settings = settings or Settings()
    configure_audit_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        validate_runtime(settings)
        app.state.settings = settings
        app.state.registry = registry or SiteRegistry.from_file(settings.site_registry_path)
        app.state.repository = repository or PostgresEnergyRepository(settings.database_url)
        app.state.authenticator = authenticator or build_authenticator(settings)
        app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
        logger.info("Product API started (env=%s, auth=%s)", settings.env, settings.auth_mode)
        yield
        dispose = getattr(app.state.repository, "dispose", None)
        if dispose:
            dispose()

    dev = settings.env == "development"
    app = FastAPI(
        title="CEI-InOE Product API",
        description="Governed data products for the dataspace. Product: site-energy-consumption-summary v1.",
        version="1.0.0",
        lifespan=lifespan,
        # Interactive docs only in development.
        docs_url="/docs" if dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if dev else None,
    )

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):
        request_id = resolve_request_id(request.headers.get("X-Request-ID"))
        request.state.audit = {"request_id": request_id}
        is_product = request.url.path.startswith("/products/")
        try:
            response = await call_next(request)
        except Exception:
            if is_product:
                emit_audit(request.state.audit, 500)
            raise
        if is_product:
            emit_audit(request.state.audit, response.status_code)
        response.headers["X-Request-ID"] = request.state.audit["request_id"]
        return response

    app.include_router(health.router, tags=["Health"])
    app.include_router(products.router, prefix="/products/v1", tags=["Products v1"])
    return app


app = create_app()
