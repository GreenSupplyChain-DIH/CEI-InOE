"""Development-only authenticator. NEVER usable in production.

How to use (local development):

    PRODUCT_API_ENV=development
    PRODUCT_API_AUTH_MODE=mock
    # optional context values reported in audit logs:
    PRODUCT_API_MOCK_PARTICIPANT=mock-participant
    PRODUCT_API_MOCK_PURPOSE=sustainability-analysis
    PRODUCT_API_MOCK_CONTRACT=mock-contract

Every request is then accepted without a token and audited as
``auth_mode=mock`` with the configured values. This is deliberately separate
from the raw CEI-InOE ``X-API-Key`` (never accepted by this service), and the
guard is enforced twice: at startup (``config.validate_runtime``) and here.
"""

from __future__ import annotations

import logging

from fastapi import Request

from app.auth import AuthorisationContext

logger = logging.getLogger(__name__)


class MockAuthenticator:
    def __init__(self, settings):
        if settings.env != "development":
            raise RuntimeError("Mock authentication is only available when PRODUCT_API_ENV=development")
        self._s = settings
        logger.warning("MOCK AUTHENTICATION ENABLED: all requests are accepted. Development only.")

    def authenticate(self, request: Request) -> AuthorisationContext:
        s = self._s
        return AuthorisationContext(
            connector_subject="mock-connector",
            participant_id=s.mock_participant,
            purpose=s.mock_purpose,
            contract_id=s.mock_contract,
            request_id=None,
            auth_mode="mock",
        )
