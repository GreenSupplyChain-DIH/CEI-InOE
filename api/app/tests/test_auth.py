"""Tests for API principal authentication and datasource access enforcement."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app import auth
from app.auth import AuthenticatedPrincipal, ensure_datasource_access
from app.routers import energy


def _energy_hourly_record(**overrides):
    values = {
        "energy_id": 1,
        "ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "energy_kwh": 12.5,
        "source_type": "api",
        "source_batch_id": UUID("12345678-1234-5678-1234-567812345678"),
        "source_device_id": "cooling-fan-1",
        "datasource_id": 45,
        "ingested_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _fake_principal_row(principal_id: int, status: str = "active", is_superuser: bool = False):
    return SimpleNamespace(id=principal_id, status=status, is_superuser=is_superuser, name="restricted-principal")


def test_hash_api_key_is_deterministic_sha256():
    key = "abc123"
    assert auth.hash_api_key(key) == hashlib.sha256(key.encode("utf-8")).hexdigest()


def test_generate_api_key_produces_unique_high_entropy_values():
    keys = {auth.generate_api_key() for _ in range(10)}
    assert len(keys) == 10
    assert all(len(k) >= 32 for k in keys)


def test_superuser_can_access_any_datasource():
    principal = AuthenticatedPrincipal(id=1, name="admin", is_superuser=True)
    assert principal.can_access_datasource(999) is True


def test_restricted_principal_only_accesses_allowed_datasources():
    principal = AuthenticatedPrincipal(
        id=2, name="cooling-fan-viewer", is_superuser=False,
        allowed_datasource_ids=frozenset({45, 67}),
    )
    assert principal.can_access_datasource(45) is True
    assert principal.can_access_datasource(99) is False


def test_ensure_datasource_access_raises_404_for_unauthorized_datasource():
    principal = AuthenticatedPrincipal(
        id=2, name="restricted", is_superuser=False, allowed_datasource_ids=frozenset({45}),
    )
    with pytest.raises(HTTPException) as exc_info:
        ensure_datasource_access(principal, 99)
    assert exc_info.value.status_code == 404


def test_ensure_datasource_access_allows_authorized_datasource():
    principal = AuthenticatedPrincipal(
        id=2, name="restricted", is_superuser=False, allowed_datasource_ids=frozenset({45}),
    )
    ensure_datasource_access(principal, 45)


def test_restricted_principal_denied_unauthorized_datasource_via_api(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7),
    )
    monkeypatch.setattr(
        auth.principal_queries, "get_datasource_ids_for_principal",
        lambda session, principal_id: [45],
    )

    response = client.get(
        "/api/v1/energy/latest",
        headers={"X-API-Key": "restricted-key"},
        params={"datasource_id": 99},
    )
    assert response.status_code == 404


def test_restricted_principal_allowed_authorized_datasource_via_api(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7),
    )
    monkeypatch.setattr(
        auth.principal_queries, "get_datasource_ids_for_principal",
        lambda session, principal_id: [45],
    )
    monkeypatch.setattr(
        energy.energy_queries, "get_latest_hourly",
        lambda session, datasource_id: _energy_hourly_record(),
    )

    response = client.get(
        "/api/v1/energy/latest",
        headers={"X-API-Key": "restricted-key"},
        params={"datasource_id": 45},
    )
    assert response.status_code == 200
    assert response.json()["datasource_id"] == 45


def test_inactive_principal_is_rejected(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7, status="suspended"),
    )

    response = client.get(
        "/api/v1/energy/latest",
        headers={"X-API-Key": "restricted-key"},
        params={"datasource_id": 45},
    )
    assert response.status_code == 403


def test_unknown_api_key_is_rejected(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: None,
    )

    response = client.get(
        "/api/v1/energy/latest",
        headers={"X-API-Key": "unknown-key"},
        params={"datasource_id": 45},
    )
    assert response.status_code == 403


def test_restricted_principal_denied_admin_endpoints(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7, is_superuser=False),
    )
    monkeypatch.setattr(
        auth.principal_queries, "get_datasource_ids_for_principal",
        lambda session, principal_id: [45],
    )

    response = client.get("/api/v1/principals", headers={"X-API-Key": "restricted-key"})
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/sites"),
        ("get", "/api/v1/batches"),
        ("get", "/api/v1/forecast/latest"),
        ("post", "/api/v1/upload/data"),
        ("get", "/api/v1/truck-deliveries/"),
    ],
)
def test_restricted_principal_cannot_access_superuser_only_routes(client, monkeypatch, method, path):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7),
    )
    monkeypatch.setattr(
        auth.principal_queries, "get_datasource_ids_for_principal",
        lambda session, principal_id: [45],
    )

    response = getattr(client, method)(path, headers={"X-API-Key": "restricted-key"})
    assert response.status_code == 403


def test_restricted_principal_energy_stats_forbidden(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7),
    )
    monkeypatch.setattr(
        auth.principal_queries, "get_datasource_ids_for_principal",
        lambda session, principal_id: [45],
    )

    response = client.get("/api/v1/energy/stats", headers={"X-API-Key": "restricted-key"})
    assert response.status_code == 403


@pytest.mark.parametrize("allowed", [[45], []])
def test_daily_energy_scopes_unfiltered_requests(client, monkeypatch, allowed):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7),
    )
    monkeypatch.setattr(
        auth.principal_queries, "get_datasource_ids_for_principal",
        lambda session, principal_id: allowed,
    )
    calls = []
    monkeypatch.setattr(
        energy.energy_queries, "get_daily",
        lambda **kwargs: (calls.append(kwargs) or [], 0),
    )
    response = client.get(
        "/api/v1/energy/daily", headers={"X-API-Key": "restricted-key"},
        params={"start_date": "2026-01-01", "end_date": "2026-01-01"},
    )
    assert response.status_code == 200
    assert calls[0]["datasource_ids"] == allowed
    assert response.json()["data"] == []


def test_daily_energy_rejects_unauthorized_datasource(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries, "get_principal_by_api_key_hash",
        lambda session, api_key_hash: _fake_principal_row(principal_id=7),
    )
    monkeypatch.setattr(
        auth.principal_queries, "get_datasource_ids_for_principal",
        lambda session, principal_id: [45],
    )
    response = client.get(
        "/api/v1/energy/daily", headers={"X-API-Key": "restricted-key"},
        params={"start_date": "2026-01-01", "end_date": "2026-01-01", "datasource_id": 99},
    )
    assert response.status_code == 404
