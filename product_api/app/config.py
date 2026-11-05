"""Product API configuration (environment variables prefixed ``PRODUCT_API_``).

Authentication modes
--------------------
``PRODUCT_API_AUTH_MODE=oidc`` (default, production)
    Every request must carry ``Authorization: Bearer <JWT>`` issued by the
    trusted OIDC issuer used by the FIWARE Data Space Connector. See
    ``app/auth_oidc.py`` for what is validated.

``PRODUCT_API_AUTH_MODE=mock`` (local development only)
    No token is checked and a fixed, clearly labelled context is used. The
    application refuses to start unless ``PRODUCT_API_ENV=development``.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRODUCT_API_", env_file=".env", extra="ignore"
    )

    env: Literal["development", "production"] = "production"
    auth_mode: Literal["oidc", "mock"] = "oidc"

    # Database: must use the read-only role (product_api_ro), see the Alembic
    # revision that creates it.
    database_url: str = ""

    # Product limits
    max_days: int = 31
    rate_limit_per_minute: int = 60  # per connector subject; 0 disables
    site_registry_path: str = "/run/secrets/product-site-registry.yaml"
    allowed_purposes: str = "sustainability-analysis"

    # OIDC / JWT validation
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_algorithms: str = "RS256,ES256"
    oidc_leeway_seconds: int = 30
    allowed_connector_client_ids: str = "fdc-provider-gateway"

    # Claim names are configurable until the FDC token layout is agreed.
    claim_client_id: str = "azp"
    claim_participant: str = "participant_id"
    claim_purpose: str = "purpose"
    claim_contract: str = "contract_id"
    claim_request_id: str = "request_id"  # optional; falls back to X-Request-ID

    # Mock mode values (development only)
    mock_participant: str = "mock-participant"
    mock_purpose: str = "sustainability-analysis"
    mock_contract: str = "mock-contract"

    audit_log_format: Literal["json"] = "json"
    incident_contact: str = "unconfigured"

    @property
    def allowed_purpose_list(self) -> list[str]:
        return _split(self.allowed_purposes)

    @property
    def allowed_client_id_list(self) -> list[str]:
        return _split(self.allowed_connector_client_ids)

    @property
    def algorithm_list(self) -> list[str]:
        return _split(self.oidc_algorithms)


def validate_runtime(settings: Settings) -> None:
    """Fail fast on unsafe or incomplete configuration."""
    if settings.auth_mode == "mock" and settings.env != "development":
        raise RuntimeError(
            "PRODUCT_API_AUTH_MODE=mock is only allowed with PRODUCT_API_ENV=development"
        )
    if settings.auth_mode == "oidc":
        missing = [
            name
            for name in ("oidc_issuer", "oidc_audience", "oidc_jwks_url")
            if not getattr(settings, name)
        ]
        if missing:
            raise RuntimeError(
                "OIDC auth requires: "
                + ", ".join(f"PRODUCT_API_{m.upper()}" for m in missing)
            )
        if not settings.allowed_client_id_list:
            raise RuntimeError("PRODUCT_API_ALLOWED_CONNECTOR_CLIENT_IDS must not be empty")
        weak = [a for a in settings.algorithm_list if a.lower() == "none" or a.upper().startswith("HS")]
        if weak or not settings.algorithm_list:
            raise RuntimeError("PRODUCT_API_OIDC_ALGORITHMS must be asymmetric (e.g. RS256, ES256)")
    if not settings.database_url:
        raise RuntimeError("PRODUCT_API_DATABASE_URL is not set")
    if settings.max_days < 1:
        raise RuntimeError("PRODUCT_API_MAX_DAYS must be >= 1")
