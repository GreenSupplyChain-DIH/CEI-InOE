"""Route-level tests for the FastAPI data API."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest

from app import auth
from app.routers import (
    batches,
    dairy,
    datasources,
    energy,
    environmental,
    forecast,
    health,
    sites,
    solar,
)


NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
BATCH_ID = UUID("12345678-1234-5678-1234-567812345678")


def datasource_record(**overrides):
    values = {
        "id": 10,
        "external_id": "meter-1",
        "source_category": "device",
        "data_type": "energy",
        "name": "Main meter",
        "alias": "main",
        "client": "cei",
        "description": "Primary energy meter",
        "status": "online",
        "timezone": "Europe/Athens",
        "metadata_": {"floor": "ground"},
        "site_id": 1,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def energy_hourly_record(**overrides):
    values = {
        "energy_id": 1,
        "ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "energy_kwh": 12.5,
        "source_type": "api",
        "source_batch_id": BATCH_ID,
        "source_device_id": "meter-1",
        "datasource_id": 10,
        "ingested_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def environmental_record(**overrides):
    values = {
        "id": 3,
        "timestamp": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "atm_pressure": 1012.3,
        "noise_level_db": 42.1,
        "temperature": 21.5,
        "humidity": 55.0,
        "pm10": 14.2,
        "wind_speed": 2.4,
        "wind_direction_sectors": 3.0,
        "wind_angle": 135.0,
        "pm2p5": 7.1,
        "source_type": "api",
        "source_batch_id": BATCH_ID,
        "source_device_id": "weather-1",
        "datasource_id": 11,
        "ingested_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def dairy_record(**overrides):
    values = {
        "id": 4,
        "production_date": date(2026, 1, 1),
        "day_production_per_cow_kg": 31.2,
        "number_of_animals": 88,
        "average_lactation_days": 145,
        "fed_per_cow_total_kg": 42.0,
        "fed_per_cow_water_kg": 12.0,
        "feed_efficiency": 1.42,
        "rumination_minutes": 510,
        "source_type": "csv",
        "source_batch_id": BATCH_ID,
        "source_device_id": "parlor-1",
        "datasource_id": 12,
        "ingested_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def solar_record(**overrides):
    values = {
        "id": 5,
        "ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "pv_yield_kwh": 45.5,
        "inverter_yield_kwh": 44.9,
        "inverter_power_kw": 6.3,
        "ongrid_power_kwh": 12.1,
        "buy_power_kwh": 2.0,
        "use_power_kwh": 35.4,
        "self_use_power_kwh": 33.4,
        "self_provide_pct": 94.3,
        "perpower_ratio": 3.2,
        "installed_capacity_kwp": 15.0,
        "power_profit": 8.7,
        "reduction_total_co2": 18.2,
        "reduction_total_coal": 7.4,
        "reduction_total_tree": 1.1,
        "source_type": "api",
        "source_batch_id": BATCH_ID,
        "source_device_id": "pv-1",
        "datasource_id": 13,
        "ingested_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def forecast_record(**overrides):
    values = {
        "id": 6,
        "forecast_run_at": datetime(2026, 1, 1, 0, tzinfo=timezone.utc),
        "valid_at": datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        "horizon_hours": 1,
        "site_id": 1,
        "shortwave_radiation_wm2": 100.0,
        "direct_radiation_wm2": 80.0,
        "direct_normal_irradiance_wm2": 90.0,
        "diffuse_radiation_wm2": 20.0,
        "global_tilted_irradiance_wm2": 110.0,
        "cloud_cover_pct": 15.0,
        "cloud_cover_low_pct": 5.0,
        "cloud_cover_mid_pct": 4.0,
        "cloud_cover_high_pct": 6.0,
        "temperature_2m_c": 18.0,
        "wind_speed_10m_ms": 3.5,
        "wind_direction_10m_deg": 180.0,
        "precipitation_mm": 0.0,
        "weather_code": 1,
        "sunshine_duration_s": 3000.0,
        "is_day": True,
        "model_id": "best_match",
        "source_batch_id": BATCH_ID,
        "source_device_id": "open-meteo",
        "ingested_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def site_record(**overrides):
    values = {
        "id": 1,
        "name": "Pilot farm",
        "location": {"type": "Point", "coordinates": [23.7, 37.9]},
        "site_type": "dairy_farm",
        "owner": {"name": "CEI"},
        "administrator_email": "admin@example.test",
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def batch_record(**overrides):
    values = {
        "batch_id": BATCH_ID,
        "source_type": "api",
        "source_name": "open-meteo",
        "datasource_id": 14,
        "granularity": "hourly",
        "date_range_start": date(2026, 1, 1),
        "date_range_end": date(2026, 1, 2),
        "file_sha256": None,
        "status": "completed",
        "records_loaded": 24,
        "records_failed": 0,
        "execution_time_ms": 250,
        "validation_status": "passed",
        "quality_score": 99.5,
        "pipeline_version": "1.0",
        "started_at": NOW,
        "completed_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def assert_page(payload, *, total=1, page=1, page_size=2):
    assert payload["total"] == total
    assert payload["page"] == page
    assert payload["page_size"] == page_size
    assert payload["total_pages"] == (total + page_size - 1) // page_size
    assert len(payload["data"]) == min(total, len(payload["data"]))


def test_root_and_health_are_public(client, monkeypatch):
    monkeypatch.setattr(health, "check_connection", lambda: True)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["health"] == "/health"

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "healthy"
    assert health_response.json()["database"] is True

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_health_reports_degraded_when_database_is_down(client, monkeypatch):
    monkeypatch.setattr(health, "check_connection", lambda: False)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] is False

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "not ready",
        "reason": "database connection failed",
    }


def test_data_routes_require_api_key(client, monkeypatch):
    monkeypatch.setattr(
        auth.principal_queries,
        "get_principal_by_api_key_hash",
        lambda session, api_key_hash: None,
    )

    assert client.get("/api/v1/energy/stats").status_code == 401
    assert client.get("/api/v1/energy/stats", headers={"X-API-Key": "wrong"}).status_code == 403


def test_energy_routes(client, auth_headers, monkeypatch, db):
    calls = {}

    def fake_get_hourly(**kwargs):
        calls["hourly"] = kwargs
        return [energy_hourly_record()], 3

    def fake_get_daily(**kwargs):
        calls["daily"] = kwargs
        return [energy.energy_queries.DailyEnergyAggregate(10, date(2026, 1, 1), 120.5, 24)], 1

    monkeypatch.setattr(energy.energy_queries, "get_hourly", fake_get_hourly)
    monkeypatch.setattr(energy.energy_queries, "get_daily", fake_get_daily)
    monkeypatch.setattr(energy.energy_queries, "get_latest_hourly", lambda session, datasource_id: energy_hourly_record())
    monkeypatch.setattr(energy.energy_queries, "get_stats", lambda session: {"count": 1})

    hourly = client.get(
        "/api/v1/energy/hourly",
        headers=auth_headers,
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "datasource_id": 10,
            "page": 2,
            "page_size": 2,
        },
    )
    assert hourly.status_code == 200
    assert_page(hourly.json(), total=3, page=2, page_size=2)
    assert hourly.json()["data"][0]["energy_kwh"] == 12.5
    assert calls["hourly"]["db"] is db
    assert calls["hourly"]["datasource_id"] == 10

    daily = client.get(
        "/api/v1/energy/daily",
        headers=auth_headers,
        params={"start_date": "2026-01-01", "end_date": "2026-01-01", "datasource_id": 10, "page_size": 2},
    )
    assert daily.status_code == 200
    assert daily.json()["data"][0] == {
        "datasource_id": 10, "ts": "2026-01-01", "energy_kwh": 120.5,
        "quality": "complete", "coverage_percent": 100.0,
    }
    assert calls["daily"]["datasource_ids"] is None

    latest = client.get("/api/v1/energy/latest", headers=auth_headers, params={"datasource_id": 10})
    assert latest.status_code == 200
    assert latest.json()["source_device_id"] == "meter-1"

    stats = client.get("/api/v1/energy/stats", headers=auth_headers)
    assert stats.status_code == 200
    assert stats.json() == {"count": 1}


@pytest.mark.parametrize("path", ["/api/v1/energy/hourly", "/api/v1/energy/daily"])
def test_energy_date_range_validation(client, auth_headers, path):
    response = client.get(
        path,
        headers=auth_headers,
        params={"start_date": "2026-01-03", "end_date": "2026-01-01", "datasource_id": 10},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "start_date must be before or equal to end_date"


def test_daily_energy_quality_pagination_and_date_limit(client, auth_headers, monkeypatch):
    calls = []

    def fake_get_daily(**kwargs):
        calls.append(kwargs)
        return [
            energy.energy_queries.DailyEnergyAggregate(10, date(2026, 1, 2), 3.0, 12),
            energy.energy_queries.DailyEnergyAggregate(11, date(2026, 1, 2), None, 0),
        ], 4

    monkeypatch.setattr(energy.energy_queries, "get_daily", fake_get_daily)
    response = client.get(
        "/api/v1/energy/daily", headers=auth_headers,
        params={"start_date": "2026-01-01", "end_date": "2026-01-02", "page": 2, "page_size": 2},
    )
    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {"datasource_id": 10, "ts": "2026-01-02", "energy_kwh": 3.0,
             "quality": "partial", "coverage_percent": 50.0},
            {"datasource_id": 11, "ts": "2026-01-02", "energy_kwh": None,
             "quality": "missing", "coverage_percent": 0.0},
        ],
        "total": 4, "page": 2, "page_size": 2, "total_pages": 2,
    }
    assert calls[0]["datasource_id"] is None
    assert calls[0]["page"] == 2

    too_long = client.get(
        "/api/v1/energy/daily", headers=auth_headers,
        params={"start_date": "2024-01-01", "end_date": "2025-01-01"},
    )
    assert too_long.status_code == 400
    assert len(calls) == 1
    accepted = client.get(
        "/api/v1/energy/daily", headers=auth_headers,
        params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
    )
    assert accepted.status_code == 200


def test_energy_latest_returns_404_when_missing(client, auth_headers, monkeypatch):
    monkeypatch.setattr(energy.energy_queries, "get_latest_hourly", lambda session, datasource_id: None)

    response = client.get("/api/v1/energy/latest", headers=auth_headers, params={"datasource_id": 10})
    assert response.status_code == 404
    assert response.json()["detail"] == "No energy data found"


def test_environmental_routes(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        environmental.env_queries,
        "get_metrics",
        lambda **kwargs: ([environmental_record()], 1),
    )
    monkeypatch.setattr(
        environmental.env_queries,
        "get_latest",
        lambda session, datasource_id: environmental_record(),
    )
    monkeypatch.setattr(environmental.env_queries, "get_stats", lambda session: {"avg_temperature": 21.5})

    hourly = client.get(
        "/api/v1/environmental/hourly",
        headers=auth_headers,
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "source_device_id": "weather-1",
            "datasource_id": 11,
            "page_size": 2,
        },
    )
    assert hourly.status_code == 200
    assert hourly.json()["data"][0]["temperature"] == 21.5

    latest = client.get("/api/v1/environmental/latest", headers=auth_headers, params={"datasource_id": 11})
    assert latest.status_code == 200
    assert latest.json()["source_device_id"] == "weather-1"

    stats = client.get("/api/v1/environmental/stats", headers=auth_headers)
    assert stats.status_code == 200
    assert stats.json() == {"avg_temperature": 21.5}


def test_environmental_error_paths(client, auth_headers, monkeypatch):
    invalid = client.get(
        "/api/v1/environmental/hourly",
        headers=auth_headers,
        params={"start_date": "2026-01-03", "end_date": "2026-01-01", "datasource_id": 11},
    )
    assert invalid.status_code == 400

    monkeypatch.setattr(environmental.env_queries, "get_latest", lambda session, datasource_id: None)
    missing = client.get("/api/v1/environmental/latest", headers=auth_headers, params={"datasource_id": 11})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "No environmental data found"


def test_dairy_routes(client, auth_headers, monkeypatch):
    monkeypatch.setattr(dairy.dairy_queries, "get_production", lambda **kwargs: ([dairy_record()], 1))
    monkeypatch.setattr(dairy.dairy_queries, "get_latest", lambda session, datasource_id: dairy_record())
    monkeypatch.setattr(dairy.dairy_queries, "get_stats", lambda session: {"animals": 88})

    daily = client.get(
        "/api/v1/dairy/daily",
        headers=auth_headers,
        params={"start_date": "2026-01-01", "end_date": "2026-01-02", "datasource_id": 12, "page_size": 2},
    )
    assert daily.status_code == 200
    assert daily.json()["data"][0]["number_of_animals"] == 88

    latest = client.get("/api/v1/dairy/latest", headers=auth_headers, params={"datasource_id": 12})
    assert latest.status_code == 200
    assert latest.json()["feed_efficiency"] == 1.42

    stats = client.get("/api/v1/dairy/stats", headers=auth_headers)
    assert stats.status_code == 200
    assert stats.json() == {"animals": 88}


def test_dairy_error_paths(client, auth_headers, monkeypatch):
    invalid = client.get(
        "/api/v1/dairy/daily",
        headers=auth_headers,
        params={"start_date": "2026-01-03", "end_date": "2026-01-01", "datasource_id": 12},
    )
    assert invalid.status_code == 400

    monkeypatch.setattr(dairy.dairy_queries, "get_latest", lambda session, datasource_id: None)
    missing = client.get("/api/v1/dairy/latest", headers=auth_headers, params={"datasource_id": 12})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "No dairy data found"


def test_solar_routes(client, auth_headers, monkeypatch):
    monkeypatch.setattr(solar.solar_queries, "get_hourly", lambda **kwargs: ([solar_record()], 1))
    monkeypatch.setattr(solar.solar_queries, "get_daily", lambda **kwargs: ([solar_record(ts=date(2026, 1, 1))], 1))
    monkeypatch.setattr(solar.solar_queries, "get_monthly", lambda **kwargs: ([solar_record(ts=date(2026, 1, 1))], 1))
    monkeypatch.setattr(solar.solar_queries, "get_latest_hourly", lambda session, datasource_id: solar_record())
    monkeypatch.setattr(solar.solar_queries, "get_stats", lambda session: {"pv_yield_kwh": 45.5})

    for path in ("/api/v1/solar/hourly", "/api/v1/solar/daily", "/api/v1/solar/monthly"):
        response = client.get(
            path,
            headers=auth_headers,
            params={"start_date": "2026-01-01", "end_date": "2026-01-02", "datasource_id": 13, "page_size": 2},
        )
        assert response.status_code == 200
        assert response.json()["data"][0]["pv_yield_kwh"] == 45.5

    latest = client.get("/api/v1/solar/latest", headers=auth_headers, params={"datasource_id": 13})
    assert latest.status_code == 200
    assert latest.json()["source_device_id"] == "pv-1"

    stats = client.get("/api/v1/solar/stats", headers=auth_headers)
    assert stats.status_code == 200
    assert stats.json() == {"pv_yield_kwh": 45.5}


@pytest.mark.parametrize("path", ["/api/v1/solar/hourly", "/api/v1/solar/daily", "/api/v1/solar/monthly"])
def test_solar_date_range_validation(client, auth_headers, path):
    response = client.get(
        path,
        headers=auth_headers,
        params={"start_date": "2026-01-03", "end_date": "2026-01-01", "datasource_id": 13},
    )
    assert response.status_code == 400


def test_solar_latest_returns_404_when_missing(client, auth_headers, monkeypatch):
    monkeypatch.setattr(solar.solar_queries, "get_latest_hourly", lambda session, datasource_id: None)

    response = client.get("/api/v1/solar/latest", headers=auth_headers, params={"datasource_id": 13})
    assert response.status_code == 404
    assert response.json()["detail"] == "No solar data found"


def test_forecast_routes(client, auth_headers, monkeypatch):
    monkeypatch.setattr(forecast.forecast_queries, "get_latest_forecast", lambda **kwargs: [forecast_record()])
    monkeypatch.setattr(forecast.forecast_queries, "get_forecast_history", lambda **kwargs: ([forecast_record()], 1))

    latest = client.get("/api/v1/forecast/latest", headers=auth_headers, params={"site_id": 1})
    assert latest.status_code == 200
    assert latest.json()[0]["model_id"] == "best_match"

    history = client.get(
        "/api/v1/forecast/history",
        headers=auth_headers,
        params={
            "valid_at_start": "2026-01-01T00:00:00Z",
            "valid_at_end": "2026-01-02T00:00:00Z",
            "site_id": 1,
            "page_size": 2,
        },
    )
    assert history.status_code == 200
    assert history.json()["data"][0]["horizon_hours"] == 1


def test_forecast_error_paths(client, auth_headers, monkeypatch):
    monkeypatch.setattr(forecast.forecast_queries, "get_latest_forecast", lambda **kwargs: [])
    missing = client.get("/api/v1/forecast/latest", headers=auth_headers, params={"site_id": 1})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "No forecast data found"

    invalid = client.get(
        "/api/v1/forecast/history",
        headers=auth_headers,
        params={"valid_at_start": "2026-01-03T00:00:00Z", "valid_at_end": "2026-01-01T00:00:00Z"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "valid_at_start must be before or equal to valid_at_end"


def test_site_routes(client, auth_headers, monkeypatch):
    monkeypatch.setattr(sites.site_queries, "get_sites", lambda session: [site_record()])
    monkeypatch.setattr(sites.site_queries, "get_site_by_id", lambda session, site_id: site_record(id=site_id))
    monkeypatch.setattr(sites.ds_queries, "get_datasources", lambda **kwargs: ([datasource_record(site_id=1)], 1))

    response = client.get("/api/v1/sites", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Pilot farm"

    datasources_response = client.get(
        "/api/v1/sites/1/datasources",
        headers=auth_headers,
        params={"data_type": "energy", "page_size": 2},
    )
    assert datasources_response.status_code == 200
    assert datasources_response.json()["data"][0]["site_id"] == 1


def test_site_datasources_returns_404_for_unknown_site(client, auth_headers, monkeypatch):
    monkeypatch.setattr(sites.site_queries, "get_site_by_id", lambda session, site_id: None)

    response = client.get("/api/v1/sites/999/datasources", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Site not found"


def test_batch_routes(client, auth_headers, monkeypatch):
    monkeypatch.setattr(batches.batch_queries, "get_batches", lambda **kwargs: ([batch_record()], 1))
    monkeypatch.setattr(
        batches.batch_queries,
        "get_batch_summary",
        lambda session: {
            "total_batches": 1,
            "completed": 1,
            "failed": 0,
            "total_records_loaded": 24,
            "total_records_failed": 0,
        },
    )
    monkeypatch.setattr(batches.batch_queries, "get_batch_by_id", lambda session, batch_id: batch_record(batch_id=batch_id))

    response = client.get("/api/v1/batches", headers=auth_headers, params={"page_size": 2})
    assert response.status_code == 200
    assert response.json()["data"][0]["records_loaded"] == 24

    summary = client.get("/api/v1/batches/summary", headers=auth_headers)
    assert summary.status_code == 200
    assert summary.json()["completed"] == 1

    batch = client.get(f"/api/v1/batches/{BATCH_ID}", headers=auth_headers)
    assert batch.status_code == 200
    assert batch.json()["batch_id"] == str(BATCH_ID)


def test_batch_returns_404_for_unknown_id(client, auth_headers, monkeypatch):
    monkeypatch.setattr(batches.batch_queries, "get_batch_by_id", lambda session, batch_id: None)

    response = client.get(f"/api/v1/batches/{BATCH_ID}", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Batch not found"


def test_datasource_read_routes(client, auth_headers, monkeypatch):
    monkeypatch.setattr(datasources.ds_queries, "get_datasources", lambda **kwargs: ([datasource_record()], 1))
    monkeypatch.setattr(datasources.ds_queries, "get_data_types", lambda session: [{"data_type": "energy", "count": 1}])
    monkeypatch.setattr(datasources.ds_queries, "get_source_categories", lambda session: [{"source_category": "device", "count": 1}])
    monkeypatch.setattr(datasources.ds_queries, "get_datasource_by_id", lambda session, datasource_id: datasource_record(id=datasource_id))
    monkeypatch.setattr(
        datasources.ds_queries,
        "get_datasource_by_external_id",
        lambda session, external_id: datasource_record(external_id=external_id),
    )

    response = client.get(
        "/api/v1/datasources",
        headers=auth_headers,
        params={"data_type": "energy", "status": "online", "site_id": 1, "page_size": 2},
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["metadata"] == {"floor": "ground"}

    types = client.get("/api/v1/datasources/types", headers=auth_headers)
    assert types.status_code == 200
    assert types.json() == [{"data_type": "energy", "count": 1}]

    categories = client.get("/api/v1/datasources/categories", headers=auth_headers)
    assert categories.status_code == 200
    assert categories.json() == [{"source_category": "device", "count": 1}]

    by_id = client.get("/api/v1/datasources/10", headers=auth_headers)
    assert by_id.status_code == 200
    assert by_id.json()["id"] == 10

    by_external = client.get("/api/v1/datasources/external/meter-1", headers=auth_headers)
    assert by_external.status_code == 200
    assert by_external.json()["external_id"] == "meter-1"


def test_datasource_missing_read_routes_return_404(client, auth_headers, monkeypatch):
    monkeypatch.setattr(datasources.ds_queries, "get_datasource_by_id", lambda session, datasource_id: None)
    monkeypatch.setattr(datasources.ds_queries, "get_datasource_by_external_id", lambda session, external_id: None)

    by_id = client.get("/api/v1/datasources/404", headers=auth_headers)
    assert by_id.status_code == 404
    assert by_id.json()["detail"] == "Datasource not found"

    by_external = client.get("/api/v1/datasources/external/missing", headers=auth_headers)
    assert by_external.status_code == 404
    assert by_external.json()["detail"] == "Datasource not found"


def test_datasource_write_routes(client, auth_headers, monkeypatch):
    captured = {}

    monkeypatch.setattr(datasources.ds_queries, "get_datasource_by_external_id", lambda session, external_id: None)
    monkeypatch.setattr(datasources.ds_queries, "get_datasource_by_id", lambda session, datasource_id: datasource_record(id=datasource_id))

    def fake_create(session, datasource):
        captured["created"] = datasource
        datasource.id = 20
        datasource.created_at = NOW
        datasource.updated_at = NOW
        return datasource

    def fake_update(session, datasource_id, **kwargs):
        captured["updated"] = kwargs
        return datasource_record(id=datasource_id, name=kwargs["name"], metadata_=kwargs["metadata_"])

    monkeypatch.setattr(datasources.ds_queries, "create_datasource", fake_create)
    monkeypatch.setattr(datasources.ds_queries, "update_datasource", fake_update)
    monkeypatch.setattr(datasources.ds_queries, "soft_delete_datasource", lambda session, datasource_id: datasource_record(id=datasource_id, status="offline"))
    monkeypatch.setattr(datasources.ds_queries, "purge_datasource", lambda session, datasource_id: {"datasource": 1, "fact_energy_hourly": 2})

    create = client.post(
        "/api/v1/datasources",
        headers=auth_headers,
        json={
            "external_id": "meter-2",
            "source_category": "device",
            "data_type": "energy",
            "name": "Secondary meter",
            "client": "cei",
            "status": "online",
            "timezone": "Europe/Athens",
            "metadata": {"phase": "B"},
            "site_id": 1,
        },
    )
    assert create.status_code == 201
    assert create.json()["id"] == 20
    assert captured["created"].metadata_ == {"phase": "B"}

    update = client.patch(
        "/api/v1/datasources/20",
        headers=auth_headers,
        json={"name": "Updated meter", "metadata": {"phase": "C"}},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Updated meter"
    assert captured["updated"] == {"name": "Updated meter", "metadata_": {"phase": "C"}}

    disable = client.delete("/api/v1/datasources/20", headers=auth_headers)
    assert disable.status_code == 200
    assert disable.json()["status"] == "offline"

    purge = client.delete("/api/v1/datasources/20/purge", headers=auth_headers)
    assert purge.status_code == 200
    assert purge.json()["rows_deleted"] == {"datasource": 1, "fact_energy_hourly": 2}


def test_datasource_write_error_paths(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        datasources.ds_queries,
        "get_datasource_by_external_id",
        lambda session, external_id: datasource_record(external_id=external_id),
    )
    duplicate = client.post(
        "/api/v1/datasources",
        headers=auth_headers,
        json={
            "external_id": "meter-1",
            "source_category": "device",
            "data_type": "energy",
            "client": "cei",
        },
    )
    assert duplicate.status_code == 409

    monkeypatch.setattr(datasources.ds_queries, "update_datasource", lambda session, datasource_id, **kwargs: None)
    missing_update = client.patch("/api/v1/datasources/404", headers=auth_headers, json={"name": "missing"})
    assert missing_update.status_code == 404

    monkeypatch.setattr(datasources.ds_queries, "soft_delete_datasource", lambda session, datasource_id: None)
    missing_disable = client.delete("/api/v1/datasources/404", headers=auth_headers)
    assert missing_disable.status_code == 404

    monkeypatch.setattr(datasources.ds_queries, "get_datasource_by_id", lambda session, datasource_id: None)
    missing_purge = client.delete("/api/v1/datasources/404/purge", headers=auth_headers)
    assert missing_purge.status_code == 404
