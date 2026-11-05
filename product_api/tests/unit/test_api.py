"""End-to-end behaviour of the endpoint (fake repository, real auth + audit)."""

import json
import logging

from conftest import FakeRepository, agg

URL = "/products/v1/site-energy-consumption-summary"
PARAMS = {"site": "site-pilot-01", "start_date": "2026-10-01", "end_date": "2026-10-02"}


def test_success_returns_only_contract_fields(client, repository, auth_headers):
    repository.rows = [agg(7, "2026-10-01", 431.2, 24), agg(7, "2026-10-02", 400.0, 24)]
    resp = client.get(URL, params=PARAMS, headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "product_id", "product_version", "site", "period", "granularity",
        "timezone", "generated_at", "data",
    }
    assert set(body["data"][0]) == {
        "date", "energy_consumption_kwh", "data_quality", "coverage_percent",
    }
    assert body["site"] == "site-pilot-01"
    assert body["granularity"] == "daily"
    # Only the allow-listed datasource of the alias is queried; ids are not exposed.
    assert repository.calls[0][0] == (7,)
    assert "7" not in json.dumps(body["site"])
    assert "datasource" not in resp.text and "device" not in resp.text


def test_alias_isolation(client, repository, auth_headers):
    client.get(URL, params={**PARAMS, "site": "site-pilot-02"}, headers=auth_headers)
    assert repository.calls[0][0] == (8,)


def test_unknown_site_is_403(client, auth_headers):
    resp = client.get(URL, params={**PARAMS, "site": "site-unknown"}, headers=auth_headers)
    assert resp.status_code == 403
    assert resp.json() == {"detail": "Access denied"}


def test_window_over_limit_is_422_not_truncated(client, repository, auth_headers):
    resp = client.get(
        URL, params={**PARAMS, "start_date": "2026-01-01", "end_date": "2026-02-01"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert repository.calls == []


def test_31_day_window_is_accepted(client, auth_headers):
    resp = client.get(
        URL, params={**PARAMS, "start_date": "2026-10-01", "end_date": "2026-10-31"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_reversed_dates_and_bad_input_are_422(client, auth_headers):
    for params in (
        {**PARAMS, "start_date": "2026-10-05", "end_date": "2026-10-01"},
        {**PARAMS, "start_date": "not-a-date"},
        {**PARAMS, "site": "Bad Site!"},
        {"site": "site-pilot-01"},
    ):
        assert client.get(URL, params=params, headers=auth_headers).status_code == 422


def test_extra_parameters_are_rejected(client, auth_headers):
    for extra in ({"fields": "x"}, {"datasource_id": 7}, {"device_id": "abc"}, {"granularity": "hourly"}):
        resp = client.get(URL, params={**PARAMS, **extra}, headers=auth_headers)
        assert resp.status_code == 422


def test_auth_required_and_x_api_key_not_accepted(client):
    assert client.get(URL, params=PARAMS).status_code == 401
    assert client.get(URL, params=PARAMS, headers={"X-API-Key": "anything"}).status_code == 401


def test_upstream_failure_is_503_without_details(client, repository, auth_headers):
    repository.fail = True
    resp = client.get(URL, params=PARAMS, headers=auth_headers)
    assert resp.status_code == 503
    assert "db down" not in resp.text


def test_rate_limit_is_429(oidc_settings, registry, rsa_key, make_token):
    from fastapi.testclient import TestClient

    from app.auth_oidc import OidcAuthenticator
    from app.main import create_app

    oidc_settings.rate_limit_per_minute = 2
    app = create_app(
        oidc_settings, registry=registry, repository=FakeRepository(),
        authenticator=OidcAuthenticator(oidc_settings, key_resolver=lambda _t: rsa_key.public_key()),
    )
    headers = {"Authorization": f"Bearer {make_token()}"}
    with TestClient(app) as c:
        codes = [c.get(URL, params=PARAMS, headers=headers).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_audit_record_for_allowed_and_denied(client, auth_headers):
    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            captured.append(record)

    handler = _Capture()
    audit_logger = logging.getLogger("product_api.audit")
    audit_logger.addHandler(handler)
    try:
        client.get(URL, params=PARAMS, headers=auth_headers)
        client.get(URL, params=PARAMS)
    finally:
        audit_logger.removeHandler(handler)

    records = [json.loads(r.getMessage()) for r in captured]
    assert len(records) == 2
    assert records[0]["outcome"] == "allowed"
    assert records[0]["site_alias"] == "site-pilot-01"
    assert records[0]["date_range_days"] == 2
    assert "authorization" not in json.dumps(records).lower()
    assert records[0]["consumer_participant_id"] == "participant-1"
    assert records[0]["policy_or_contract_id"] == "contract-123"
    assert records[1]["outcome"] == "denied" and records[1]["status_code"] == 401


def test_request_id_header_is_returned(client, auth_headers):
    resp = client.get(URL, params=PARAMS, headers={**auth_headers, "X-Request-ID": "abc-12345678"})
    assert resp.headers["X-Request-ID"] == "abc-12345678"
    bad = client.get(URL, params=PARAMS, headers={**auth_headers, "X-Request-ID": "x y\n"})
    assert bad.headers["X-Request-ID"] != "x y\n"


def test_health_ready_and_docs_hidden_in_production(client, repository):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    repository.fail = True
    assert client.get("/ready").status_code == 503
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_no_cors_headers(client, auth_headers):
    resp = client.get(URL, params=PARAMS, headers={**auth_headers, "Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in resp.headers
