"""OIDC / JWT validation of the FIWARE Data Space Connector (FDC) caller.

Vocabulary
----------
JWT   A signed token ``header.payload.signature``. Payload fields are *claims*.
JWKS  JSON Web Key Set: a JSON document published by the issuer (see
      ``PRODUCT_API_OIDC_JWKS_URL``, usually ``<issuer>/.well-known/jwks.json``
      or the ``jwks_uri`` of the issuer's OIDC discovery document) that lists
      the issuer's *public* signing keys. The key matching the token's ``kid``
      header verifies the signature, so no shared secret is needed. On key
      rotation the issuer publishes the new key and this service picks it up
      when it sees an unknown ``kid``.
iss   Issuer: who created the token. Must equal ``PRODUCT_API_OIDC_ISSUER``
      exactly, otherwise any other identity provider could mint accepted tokens.
aud   Audience: who the token is meant for. Must contain
      ``PRODUCT_API_OIDC_AUDIENCE`` (this API's identifier) so a token issued
      for another service cannot be replayed here.
exp   Expiry: the token is invalid after this time (required). Short-lived
      tokens limit damage from theft and support revocation targets.
nbf   Not-before: the token is invalid before this time (checked when present).
      ``exp``/``nbf`` are evaluated with ``PRODUCT_API_OIDC_LEEWAY_SECONDS`` of
      clock-skew tolerance.

Additionally enforced: asymmetric algorithm allow-list (``none``/``HS*`` are
refused by configuration validation), the caller's client id (claim
``PRODUCT_API_CLAIM_CLIENT_ID``, default ``azp``) must be one of
``PRODUCT_API_ALLOWED_CONNECTOR_CLIENT_IDS``, and participant, purpose and
contract claims must be present (claim names are configurable). The purpose
must be one of ``PRODUCT_API_ALLOWED_PURPOSES``.

Result codes: 401 = missing/invalid/expired token or unexpected client;
403 = authenticated but missing context claims or purpose not allowed.

How to use
----------
Production: set the ``PRODUCT_API_OIDC_*`` variables and keep
``PRODUCT_API_AUTH_MODE=oidc``; the FDC gateway sends
``Authorization: Bearer <JWT>``.

Local testing without an issuer: use ``PRODUCT_API_AUTH_MODE=mock`` with
``PRODUCT_API_ENV=development`` (see ``app/auth_mock.py``), or in tests mint a
token with a throw-away RSA key and inject a ``key_resolver`` returning its
public key (see ``tests/conftest.py``):

    token = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "exp": now + 300, "azp": "fdc-provider-gateway",
         "participant_id": "p-1", "purpose": "sustainability-analysis",
         "contract_id": "c-1"},
        private_key, algorithm="RS256", headers={"kid": "test"},
    )
"""

from __future__ import annotations

import logging
from typing import Callable

import jwt
from fastapi import Request

from app.auth import AuthorisationContext, forbidden, unauthorised

logger = logging.getLogger(__name__)

KeyResolver = Callable[[str], object]


class OidcAuthenticator:
    def __init__(self, settings, key_resolver: KeyResolver | None = None):
        self._s = settings
        if key_resolver is None:
            # Fetches/caches the issuer's JWKS and selects the key by `kid`.
            jwk_client = jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True)
            key_resolver = lambda token: jwk_client.get_signing_key_from_jwt(token).key  # noqa: E731
        self._resolve_key = key_resolver

    def authenticate(self, request: Request) -> AuthorisationContext:
        scheme, _, token = (request.headers.get("Authorization") or "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise unauthorised()

        s = self._s
        try:
            claims = jwt.decode(
                token,
                key=self._resolve_key(token),
                algorithms=s.algorithm_list,
                audience=s.oidc_audience,
                issuer=s.oidc_issuer,
                leeway=s.oidc_leeway_seconds,
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            # Log the reason server-side only; never echo it to the caller.
            logger.warning("Token rejected: %s", type(exc).__name__)
            raise unauthorised() from exc
        except Exception as exc:  # e.g. JWKS endpoint unreachable
            logger.error("Token verification failed: %s", type(exc).__name__)
            raise unauthorised() from exc

        client_id = claims.get(s.claim_client_id)
        if client_id not in s.allowed_client_id_list:
            logger.warning("Token rejected: unexpected client")
            raise unauthorised()

        participant = claims.get(s.claim_participant)
        purpose = claims.get(s.claim_purpose)
        contract = claims.get(s.claim_contract)
        if not (participant and purpose and contract):
            logger.warning("Token rejected: missing context claims")
            raise forbidden()
        if purpose not in s.allowed_purpose_list:
            logger.warning("Token rejected: purpose not allowed")
            raise forbidden()

        return AuthorisationContext(
            connector_subject=str(client_id),
            participant_id=str(participant),
            purpose=str(purpose),
            contract_id=str(contract),
            request_id=claims.get(s.claim_request_id),
            auth_mode="oidc",
        )
