"""Read access to hourly energy data.

Only the purpose-built view ``product_energy_hourly_v1`` is queried (columns
``ts``, ``energy_kwh``, ``datasource_id``); the read-only database role has no
access to the underlying tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine

from app.services.site_access import DatasourceConfig


@dataclass(frozen=True)
class DailyAggregate:
    datasource_id: int
    day: date  # calendar day in the reporting timezone
    energy_kwh: float
    hours_present: int


class EnergyRepository(Protocol):
    def daily_aggregates(
        self,
        datasources: Sequence[DatasourceConfig],
        reporting_tz: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[DailyAggregate]:
        """Return hourly energy totals grouped by datasource and reporting-local day.

        Include readings in the half-open UTC interval
        ``start_utc <= instant < end_utc``. Each result contains the day's
        energy total and the number of hourly readings present for that
        datasource; timestamps are interpreted in each datasource's timezone
        before being assigned to a day in ``reporting_tz``.
        """
        ...

    def ping(self) -> bool: ...


# `ts` is a naive timestamp stored in the datasource's own timezone. It is
# interpreted in that timezone (AT TIME ZONE src -> timestamptz) and then
# rendered in the reporting timezone (AT TIME ZONE rep) before taking the day.
# During the autumn DST change one local hour repeats; the stored naive values
# are unique per datasource, so nothing is double-counted.
_DAILY_SQL = text(
    """
    SELECT datasource_id,
           ((ts AT TIME ZONE :src_tz) AT TIME ZONE :rep_tz)::date AS day,
           SUM(energy_kwh) AS energy_kwh,
           COUNT(*) AS hours_present
    FROM product_energy_hourly_v1
    WHERE datasource_id IN :ds_ids
      AND ts >= :start_ts AND ts < :end_ts
    GROUP BY datasource_id, day
    ORDER BY day
    """
).bindparams(bindparam("ds_ids", expanding=True))


class PostgresEnergyRepository:
    def __init__(self, database_url: str, engine: Engine | None = None):
        self._engine = engine or create_engine(
            database_url, pool_size=5, max_overflow=5, pool_pre_ping=True
        )

    def daily_aggregates(
        self,
        datasources: Sequence[DatasourceConfig],
        reporting_tz: str,
        start_utc: datetime,
        end_utc: datetime,
    ) -> list[DailyAggregate]:
        by_tz: dict[str, list[int]] = {}
        for ds in datasources:
            by_tz.setdefault(ds.ts_timezone, []).append(ds.id)

        results: list[DailyAggregate] = []
        with self._engine.connect() as conn:
            for src_tz, ids in by_tz.items():
                zone = ZoneInfo(src_tz)
                # Bounds are converted to the storage timezone so the plain
                # `ts` column (and its index) can be filtered directly.
                start_ts = start_utc.astimezone(zone).replace(tzinfo=None)
                end_ts = end_utc.astimezone(zone).replace(tzinfo=None)
                rows = conn.execute(
                    _DAILY_SQL,
                    {
                        "src_tz": src_tz,
                        "rep_tz": reporting_tz,
                        "ds_ids": ids,
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                    },
                )
                results.extend(
                    DailyAggregate(
                        datasource_id=r.datasource_id,
                        day=r.day,
                        energy_kwh=float(r.energy_kwh),
                        hours_present=int(r.hours_present),
                    )
                    for r in rows
                )
        return results

    def ping(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def dispose(self) -> None:
        self._engine.dispose()
