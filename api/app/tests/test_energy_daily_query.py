"""PostgreSQL tests for daily aggregation of hourly energy."""

import os
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth import AuthenticatedPrincipal, verify_api_key
from app.db.session import get_db
from app.db.queries.energy import DailyEnergyAggregate, get_daily
from app.main import app


@pytest.fixture
def energy_db():
    url = os.environ.get("API_TEST_DATABASE_URL")
    if not url:
        pytest.skip("API_TEST_DATABASE_URL is required for PostgreSQL query tests")
    engine = create_engine(url)
    with engine.connect() as connection:
        connection.execute(text("""
            CREATE TEMPORARY TABLE datasource (
                id integer PRIMARY KEY, data_type text NOT NULL, status text NOT NULL
            ) ON COMMIT DROP
        """))
        connection.execute(text("""
            CREATE TEMPORARY TABLE fact_energy_hourly (
                datasource_id integer, ts timestamp NOT NULL, energy_kwh double precision NOT NULL
            ) ON COMMIT DROP
        """))
        connection.execute(text("""
            INSERT INTO datasource VALUES
                (1, 'energy', 'online'), (2, 'energy', 'online'),
                (3, 'energy', 'offline'), (4, 'weather', 'online')
        """))
        connection.execute(text("""
            INSERT INTO fact_energy_hourly
            SELECT 1, timestamp '2026-01-01' + n * interval '1 hour', 1.0
            FROM generate_series(0, 23) AS n
        """))
        connection.execute(text("""
            INSERT INTO fact_energy_hourly VALUES
                (1, '2026-01-01 00:30', 2),
                (1, '2026-01-02 12:00', 3),
                (1, '2026-01-02 12:30', 4),
                (1, '2025-12-31 23:00', 99),
                (1, '2026-01-03 00:00', 99),
                (3, '2026-01-01 00:00', 99),
                (4, '2026-01-01 00:00', 99),
                (NULL, '2026-01-01 00:00', 99)
        """))
        with Session(bind=connection) as session:
            yield session
        connection.rollback()
    engine.dispose()


def test_daily_query_sums_hours_generates_missing_days_and_paginates(energy_db):
    kwargs = dict(db=energy_db, start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))
    records, total = get_daily(**kwargs, page_size=2)
    assert total == 4
    assert records == [
        DailyEnergyAggregate(1, date(2026, 1, 2), 7.0, 1),
        DailyEnergyAggregate(2, date(2026, 1, 2), None, 0),
    ]
    records, total = get_daily(**kwargs, page=2, page_size=2)
    assert total == 4
    assert records == [
        DailyEnergyAggregate(1, date(2026, 1, 1), 26.0, 24),
        DailyEnergyAggregate(2, date(2026, 1, 1), None, 0),
    ]
    assert get_daily(**kwargs, page=3, page_size=2) == ([], 4)


def test_daily_query_filters_access_and_online_energy_datasources(energy_db):
    kwargs = dict(db=energy_db, start_date=date(2026, 1, 1), end_date=date(2026, 1, 1))
    assert get_daily(**kwargs, datasource_ids=[]) == ([], 0)
    assert get_daily(**kwargs, datasource_ids=[2]) == (
        [DailyEnergyAggregate(2, date(2026, 1, 1), None, 0)], 1
    )
    assert get_daily(**kwargs, datasource_id=1, datasource_ids=[2]) == ([], 0)
    assert get_daily(**kwargs, datasource_id=3) == ([], 0)
    assert get_daily(**kwargs, datasource_id=4) == ([], 0)
    assert get_daily(**kwargs, datasource_id=999) == ([], 0)
    assert get_daily(**kwargs, datasource_id=1) == (
        [DailyEnergyAggregate(1, date(2026, 1, 1), 26.0, 24)], 1
    )


def test_daily_endpoint_uses_hourly_aggregates(client, auth_headers, energy_db):
    app.dependency_overrides[get_db] = lambda: energy_db
    response = client.get(
        "/api/v1/energy/daily",
        headers=auth_headers,
        params={"start_date": "2026-01-01", "end_date": "2026-01-02", "page_size": 4},
    )
    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {"datasource_id": 1, "ts": "2026-01-02", "energy_kwh": 7.0,
             "quality": "partial", "coverage_percent": 100.0 / 24},
            {"datasource_id": 2, "ts": "2026-01-02", "energy_kwh": None,
             "quality": "missing", "coverage_percent": 0.0},
            {"datasource_id": 1, "ts": "2026-01-01", "energy_kwh": 26.0,
             "quality": "complete", "coverage_percent": 100.0},
            {"datasource_id": 2, "ts": "2026-01-01", "energy_kwh": None,
             "quality": "missing", "coverage_percent": 0.0},
        ],
        "total": 4, "page": 1, "page_size": 4, "total_pages": 1,
    }


@pytest.mark.parametrize("allowed", [[2], []])
def test_daily_endpoint_filters_real_database_by_principal(client, energy_db, allowed):
    app.dependency_overrides[get_db] = lambda: energy_db
    app.dependency_overrides[verify_api_key] = lambda: AuthenticatedPrincipal(
        id=1, name="restricted", is_superuser=False, allowed_datasource_ids=frozenset(allowed)
    )
    response = client.get(
        "/api/v1/energy/daily",
        params={"start_date": "2026-01-01", "end_date": "2026-01-01"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == len(allowed)
    assert [row["datasource_id"] for row in response.json()["data"]] == allowed


def test_daily_query_maximum_range_counts_missing_days(energy_db):
    records, total = get_daily(
        energy_db, date(2024, 1, 1), date(2024, 12, 31), page_size=1
    )
    assert total == 732
    assert records == [DailyEnergyAggregate(1, date(2024, 12, 31), None, 0)]
