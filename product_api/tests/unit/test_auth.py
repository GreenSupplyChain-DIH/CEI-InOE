"""OIDC validation, mock-mode guard and configuration checks."""

import time

import jwt
import pytest
from fastapi import HTTPException

from app.auth_mock import MockAuthenticator
from app.auth_oidc import OidcAuthenticator
from app.config import Settings, validate_runtime

from conftest import CLIENT_ID


class FakeRequest:
    def __init__(self, token: str | None):
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}


@pytest.fixture
def authn(oidc_settings, rsa_key):
    return OidcAuthenticator(oidc_settings, key_resolver=lambda _t: rsa_key.public_key())


def test_valid_token_builds_context(authn, make_token):
    ctx = authn.authenticate(FakeRequest(make_token()))
    assert ctx.connector_subject == CLIENT_ID
    assert ctx.participant_id == "participant-1"
    assert ctx.contract_id == "contract-123"
    assert ctx.auth_mode == "oidc"


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://evil.example.org"},
        {"aud": "another-service"},
        {"exp": int(time.time()) - 3600},
        {"nbf": int(time.time()) + 3600},
        {"azp": "unknown-client"},
        {"exp": None},
    ],
)
def test_invalid_tokens_are_401(authn, make_token, overrides):
    with pytest.raises(HTTPException) as exc:
        authn.authenticate(FakeRequest(make_token(**overrides)))
    assert exc.value.status_code == 401


def test_missing_or_malformed_header_is_401(authn):
    for req in (FakeRequest(None), FakeRequest("")):
        with pytest.raises(HTTPException) as exc:
            authn.authenticate(req)
        assert exc.value.status_code == 401


def test_wrong_signature_is_401(oidc_settings, make_token):
    from cryptography.hazmat.primitives.asymmetric import rsa

    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    authn = OidcAuthenticator(oidc_settings, key_resolver=lambda _t: other.public_key())
    with pytest.raises(HTTPException) as exc:
        authn.authenticate(FakeRequest(make_token()))
    assert exc.value.status_code == 401


def test_hs256_token_is_rejected(authn):
    token = jwt.encode(
        {"iss": "https://issuer.example.org/realms/fdc", "aud": "cei-inoe-product-api",
         "exp": int(time.time()) + 60, "azp": CLIENT_ID},
        "x" * 40,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        authn.authenticate(FakeRequest(token))
    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [{"participant_id": None}, {"purpose": None}, {"contract_id": None}, {"purpose": "marketing"}],
)
def test_missing_context_or_wrong_purpose_is_403(authn, make_token, overrides):
    with pytest.raises(HTTPException) as exc:
        authn.authenticate(FakeRequest(make_token(**overrides)))
    assert exc.value.status_code == 403


def test_mock_refused_outside_development():
    prod = Settings(env="production", auth_mode="mock", database_url="x")
    with pytest.raises(RuntimeError):
        validate_runtime(prod)
    with pytest.raises(RuntimeError):
        MockAuthenticator(prod)


def test_mock_allowed_in_development():
    dev = Settings(env="development", auth_mode="mock", database_url="x")
    validate_runtime(dev)
    ctx = MockAuthenticator(dev).authenticate(FakeRequest(None))
    assert ctx.auth_mode == "mock"


def test_oidc_requires_issuer_audience_jwks():
    with pytest.raises(RuntimeError):
        validate_runtime(Settings(env="production", auth_mode="oidc", database_url="x"))


def test_symmetric_algorithms_refused(oidc_settings):
    oidc_settings.oidc_algorithms = "HS256"
    with pytest.raises(RuntimeError):
        validate_runtime(oidc_settings)
