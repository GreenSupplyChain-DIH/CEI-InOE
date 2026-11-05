"""Connector authentication: produces the ``AuthorisationContext`` used by routes.

Two interchangeable authenticators exist, selected by ``PRODUCT_API_AUTH_MODE``:

* ``oidc`` (production): ``app/auth_oidc.py`` validates the connector's JWT.
* ``mock`` (development only): ``app/auth_mock.py``; the app refuses to start
  in mock mode unless ``PRODUCT_API_ENV=development``.

The raw CEI-InOE ``X-API-Key`` is intentionally never accepted here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class AuthorisationContext:
    connector_subject: str
    participant_id: str
    purpose: str
    contract_id: str
    request_id: str | None
    auth_mode: str


class Authenticator(Protocol):
    def authenticate(self, request: Request) -> AuthorisationContext: ...


def unauthorised(detail: str = "Invalid or missing credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(detail: str = "Access denied") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def build_authenticator(settings) -> Authenticator:
    # Imported lazily so mock code is never loaded in oidc mode.
    if settings.auth_mode == "mock":
        from app.auth_mock import MockAuthenticator

        return MockAuthenticator(settings)
    from app.auth_oidc import OidcAuthenticator

    return OidcAuthenticator(settings)
