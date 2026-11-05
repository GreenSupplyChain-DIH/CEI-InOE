"""Daily aggregation, quality rules and DST handling."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.services.site_access import SiteRegistry
from app.services.site_energy_consumption import build_summary, expected_hours

from conftest import FakeRepository, agg

NICOSIA = ZoneInfo("Asia/Nicosia")
NOW = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)


def test_expected_hours_on_dst_days():
    from datetime import date

    assert expected_hours(date(2026, 3, 29), NICOSIA) == 23  # spring forward
    assert expected_hours(date(2026, 10, 25), NICOSIA) == 25  # fall back
    assert expected_hours(date(2026, 10, 1), NICOSIA) == 24


def test_complete_partial_missing(registry):
    site = registry.get("site-pilot-01")
    repo = FakeRepository(
        [agg(7, "2026-10-01", 431.2, 24), agg(7, "2026-10-02", 100.0, 12)]
    )
    from datetime import date

    summary = build_summary(site, date(2026, 10, 1), date(2026, 10, 3), repo, now=NOW)

    assert [d.data_quality for d in summary.data] == ["complete", "partial", "missing"]
    assert summary.data[0].energy_consumption_kwh == 431.2
    assert summary.data[1].coverage_percent == 50.0
    assert summary.data[2].energy_consumption_kwh is None
    assert summary.timezone == "Asia/Nicosia"


def test_dst_day_complete_with_23_hours(registry):
    from datetime import date

    site = registry.get("site-pilot-01")
    repo = FakeRepository([agg(7, "2026-03-29", 50.0, 23)])
    summary = build_summary(site, date(2026, 3, 29), date(2026, 3, 29), repo, now=NOW)
    assert summary.data[0].data_quality == "complete"


def test_future_days_are_not_returned(registry):
    from datetime import date

    site = registry.get("site-pilot-01")
    repo = FakeRepository()
    summary = build_summary(site, date(2026, 11, 3), date(2026, 11, 10), repo, now=NOW)
    assert [d.date.isoformat() for d in summary.data] == ["2026-11-03"]
    # Query window ends at the end of today, never in the future.
    assert repo.calls[0][3] == datetime(2026, 11, 3, 22, 0, tzinfo=timezone.utc)


def test_entirely_future_range_does_not_query(registry):
    from datetime import date

    repo = FakeRepository()
    summary = build_summary(
        registry.get("site-pilot-01"), date(2026, 12, 1), date(2026, 12, 2), repo, now=NOW
    )
    assert summary.data == [] and repo.calls == []


def test_multiple_datasources_are_summed_and_coverage_scales():
    from datetime import date

    registry = SiteRegistry.from_dict(
        {"sites": {"site-two-ds": {"timezone": "UTC", "datasources": [{"id": 1}, {"id": 2}]}}}
    )
    repo = FakeRepository([agg(1, "2026-10-01", 10.0, 24), agg(2, "2026-10-01", 5.0, 12)])
    summary = build_summary(
        registry.get("site-two-ds"), date(2026, 10, 1), date(2026, 10, 1), repo, now=NOW
    )
    assert summary.data[0].energy_consumption_kwh == 15.0
    assert summary.data[0].data_quality == "partial"
    assert summary.data[0].coverage_percent == 75.0


def test_registry_rejects_unknown_timezone():
    import pytest

    with pytest.raises(ValueError):
        SiteRegistry.from_dict(
            {"sites": {"site-x-01": {"timezone": "Mars/Base", "datasources": [{"id": 1}]}}}
        )
