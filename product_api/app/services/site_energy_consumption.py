"""Builds the daily site energy consumption product from hourly aggregates."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.repositories.energy_repository import EnergyRepository
from app.schemas.product_v1 import DailyEnergy, Period, SiteEnergySummary
from app.services.site_access import SiteConfig


def _local_midnight_utc(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)


def expected_hours(day: date, tz: ZoneInfo) -> int:
    """Hours in a local calendar day: 23/25 on daylight-saving change days."""
    span = _local_midnight_utc(day + timedelta(days=1), tz) - _local_midnight_utc(day, tz)
    return round(span.total_seconds() / 3600)


def build_summary(
    site: SiteConfig,
    start_date: date,
    end_date: date,
    repository: EnergyRepository,
    now: datetime | None = None,
) -> SiteEnergySummary:
    """Build a daily energy summary for a site over the requested date range.

    A day is ``complete`` only when every expected hour is present for every
    datasource; otherwise it is ``partial`` with a coverage percentage, or
    ``missing`` when there is no data. Days that have not started yet in the
    site's timezone are not returned.
    """
    now = now or datetime.now(timezone.utc)
    tz = ZoneInfo(site.timezone)
    today = now.astimezone(tz).date()

    last_day = min(end_date, today)
    rows = []
    if start_date <= last_day:
        rows = repository.daily_aggregates(
            site.datasources,
            site.timezone,
            _local_midnight_utc(start_date, tz),
            _local_midnight_utc(last_day + timedelta(days=1), tz),
        )

    energy: dict[date, float] = defaultdict(float)
    hours: dict[date, int] = defaultdict(int)
    for row in rows:
        energy[row.day] += row.energy_kwh
        hours[row.day] += row.hours_present

    data: list[DailyEnergy] = []
    day = start_date
    while day <= last_day:
        expected = expected_hours(day, tz) * len(site.datasources)
        present = hours.get(day, 0)
        coverage = min(100.0, round(100.0 * present / expected, 1))
        if present == 0:
            quality, total = "missing", None
        else:
            quality = "complete" if present >= expected else "partial"
            total = round(energy[day], 3)
        data.append(
            DailyEnergy(
                date=day,
                energy_consumption_kwh=total,
                data_quality=quality,
                coverage_percent=coverage,
            )
        )
        day += timedelta(days=1)

    return SiteEnergySummary(
        site=site.alias,
        period=Period(start_date=start_date, end_date=end_date),
        timezone=site.timezone,
        generated_at=now,
        data=data,
    )
