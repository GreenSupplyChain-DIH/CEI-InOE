"""Shared test fixtures for the Product API."""

from __future__ import annotations

import sys
import time
from datetime import date, datetime
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

PRODUCT_API_ROOT = Path(__file__).resolve().parents[1]
if str(PRODUCT_API_ROOT) not in sys.path:
    sys.path.insert(0, str(PRODUCT_API_ROOT))

from app.auth_oidc import OidcAuthenticator  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repositories.energy_repository import DailyAggregate  # noqa: E402
from app.services.site_access import SiteRegistry  # noqa: E402

ISSUER = "https://issuer.example.org/realms/fdc"
AUDIENCE = "cei-inoe-product-api"
CLIENT_ID = "fdc-provider-gateway"


@pytest.fixture(autouse=True)
def _isolate_settings_from_environment(monkeypatch):
    """Tests must not depend on a developer's .env or PRODUCT_API_* variables."""
    import os

    for name in list(os.environ):
        if name.startswith("PRODUCT_API_"):
            monkeypatch.delenv(name)
    monkeypatch.setitem(Settings.model_config, "env_file", None)


class FakeRepository:
    """In-memory repository; records the calls it receives."""

    def __init__(self, rows: list[DailyAggregate] | None = None, fail: bool = False):
        self.rows = rows or []
        self.fail = fail
        self.calls: list[tuple] = []

    def daily_aggregates(self, datasources, reporting_tz, start_utc, end_utc):
        self.calls.append((tuple(d.id for d in datasources), reporting_tz, start_utc, end_utc))
        if self.fail:
            from sqlalchemy.exc import OperationalError

            raise OperationalError("select", {}, Exception("db down"))
        return list(self.rows)

    def ping(self) -> bool:
        return not self.fail


@pytest.fixture(scope="session")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def make_token(rsa_key):
    def _make(**overrides) -> str:
        claims = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": int(time.time()) + 300,
            "azp": CLIENT_ID,
            "participant_id": "participant-1",
            "purpose": "sustainability-analysis",
            "contract_id": "contract-123",
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, rsa_key, algorithm="RS256", headers={"kid": "test"})

    return _make


@pytest.fixture
def oidc_settings() -> Settings:
    return Settings(
        env="production",
        auth_mode="oidc",
        database_url="postgresql://ro@localhost/x",
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_jwks_url="https://issuer.example.org/jwks",
        allowed_connector_client_ids=CLIENT_ID,
        rate_limit_per_minute=0,
    )


@pytest.fixture
def registry() -> SiteRegistry:
    return SiteRegistry.from_dict(
        {
            "sites": {
                "site-pilot-01": {
                    "timezone": "Asia/Nicosia",
                    "datasources": [{"id": 7, "ts_timezone": "Asia/Nicosia"}],
                },
                "site-pilot-02": {
                    "timezone": "Asia/Nicosia",
                    "datasources": [{"id": 8, "ts_timezone": "UTC"}],
                },
            }
        }
    )


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def client(oidc_settings, registry, repository, rsa_key):
    authenticator = OidcAuthenticator(oidc_settings, key_resolver=lambda _t: rsa_key.public_key())
    app = create_app(
        oidc_settings, registry=registry, repository=repository, authenticator=authenticator
    )
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(make_token):
    return {"Authorization": f"Bearer {make_token()}"}


def agg(ds: int, day: str, kwh: float, hours: int) -> DailyAggregate:
    return DailyAggregate(
        datasource_id=ds, day=date.fromisoformat(day), energy_kwh=kwh, hours_present=hours
    )
