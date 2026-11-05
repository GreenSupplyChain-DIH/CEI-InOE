"""Repository SQL against a real PostgreSQL.

Skipped unless PRODUCT_API_TEST_DATABASE_URL points at a disposable database.
The test creates and drops its own schema ``papi_test`` and never touches other objects.
"""

import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text

from app.repositories.energy_repository import PostgresEnergyRepository
from app.services.site_access import DatasourceConfig

URL = os.getenv("PRODUCT_API_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="PRODUCT_API_TEST_DATABASE_URL not set")


@pytest.fixture
def repo():
    admin = create_engine(URL)
    with admin.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS papi_test CASCADE"))
        conn.execute(text("CREATE SCHEMA papi_test"))
        conn.execute(
            text(
                "CREATE TABLE papi_test.product_energy_hourly_v1 "
                "(ts timestamp NOT NULL, energy_kwh double precision NOT NULL, datasource_id int NOT NULL)"
            )
        )
    scoped = create_engine(URL, connect_args={"options": "-c search_path=papi_test"})
    yield PostgresEnergyRepository(URL, engine=scoped), admin
    scoped.dispose()
    with admin.begin() as conn:
        conn.execute(text("DROP SCHEMA papi_test CASCADE"))
    admin.dispose()


def _insert(admin, rows):
    with admin.begin() as conn:
        for ds, ts, kwh in rows:
            conn.execute(
                text("INSERT INTO papi_test.product_energy_hourly_v1 VALUES (:ts, :k, :d)"),
                {"ts": ts, "k": kwh, "d": ds},
            )


def test_local_day_grouping_and_datasource_scoping(repo):
    repository, admin = repo
    # ds 1 stores Cyprus-local naive time; ds 2 stores UTC naive time. Both report in Asia/Nicosia (UTC+3 in Oct).
    _insert(
        admin,
        [
            (1, "2026-10-01 00:00", 1.0),
            (1, "2026-10-01 23:00", 2.0),
            (1, "2026-10-02 00:00", 4.0),
            (2, "2026-10-01 21:00", 8.0),  # 00:00 local on 2 Oct
            (3, "2026-10-01 10:00", 99.0),  # not allow-listed
        ],
    )
    rows = repository.daily_aggregates(
        [DatasourceConfig(1, "Asia/Nicosia"), DatasourceConfig(2, "UTC")],
        "Asia/Nicosia",
        datetime(2026, 9, 30, 21, 0, tzinfo=timezone.utc),  # local midnight 1 Oct
        datetime(2026, 10, 2, 21, 0, tzinfo=timezone.utc),  # local midnight 3 Oct
    )
    got = {(r.datasource_id, r.day.isoformat()): (r.energy_kwh, r.hours_present) for r in rows}
    assert got == {
        (1, "2026-10-01"): (3.0, 2),
        (1, "2026-10-02"): (4.0, 1),
        (2, "2026-10-02"): (8.0, 1),
    }
    assert all(r.datasource_id != 3 for r in rows)


def test_ping(repo):
    assert repo[0].ping() is True
