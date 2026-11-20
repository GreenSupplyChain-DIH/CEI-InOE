"""Energy queries."""

from dataclasses import dataclass
from datetime import date, datetime
from sqlalchemy import bindparam, func, text
from sqlalchemy.orm import Session

from shared import FactEnergyHourly, FactEnergyDaily, IngestBatch


def get_hourly(
    db: Session,
    start_date: date,
    end_date: date,
    datasource_id: int | None = None,
    page: int = 1,
    page_size: int = 100
) -> tuple[list[FactEnergyHourly], int]:
    """
    Get hourly energy records with optional filters.
    
    Returns:
        Tuple of (records, total_count)
    """
    # Convert dates to datetime for comparison
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    query = db.query(FactEnergyHourly).filter(
        FactEnergyHourly.ts >= start_dt,
        FactEnergyHourly.ts <= end_dt
    )
    
    if datasource_id:
        query = query.join(
            IngestBatch, FactEnergyHourly.source_batch_id == IngestBatch.batch_id
        ).filter(IngestBatch.datasource_id == datasource_id)
    
    total = query.count()
    
    records = query.order_by(FactEnergyHourly.ts.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return records, total


@dataclass(frozen=True)
class DailyEnergyAggregate:
    datasource_id: int
    ts: date
    energy_kwh: float | None
    observed_hours: int


def get_daily(
    db: Session,
    start_date: date,
    end_date: date,
    datasource_id: int | None = None,
    datasource_ids: list[int] | None = None,
    page: int = 1,
    page_size: int = 100
) -> tuple[list[DailyEnergyAggregate], int]:
    """Aggregate hourly facts for each eligible datasource and requested day."""
    conditions = ["data_type = 'energy'", "status = 'online'"]
    days = (end_date - start_date).days + 1
    params: dict[str, date | int | list[int]] = {
        "start_date": start_date,
        "days": days,
        "offset": (page - 1) * page_size,
        "page_size": page_size,
    }
    if datasource_id is not None:
        conditions.append("id = :datasource_id")
        params["datasource_id"] = datasource_id
    if datasource_ids is not None:
        conditions.append("id IN :datasource_ids")
        params["datasource_ids"] = datasource_ids

    eligible = " AND ".join(conditions)
    count_sql = text(f"SELECT count(*) FROM datasource WHERE {eligible}")
    daily_sql = text(f"""
        WITH page AS (
            SELECT d.id AS datasource_id, CAST(:start_date AS date) + n.day_offset AS day
            FROM datasource AS d
            CROSS JOIN generate_series(0, :days - 1) AS n(day_offset)
            WHERE {eligible}
            ORDER BY day DESC, d.id ASC
            OFFSET :offset LIMIT :page_size
        )
        SELECT page.datasource_id, page.day AS ts,
               sum(h.energy_kwh) AS energy_kwh,
               count(DISTINCT extract(hour FROM h.ts)) AS observed_hours
        FROM page
        LEFT JOIN fact_energy_hourly AS h
          ON h.datasource_id = page.datasource_id
         AND h.ts >= CAST(page.day AS timestamp)
         AND h.ts < CAST(page.day AS timestamp) + interval '1 day'
        GROUP BY page.datasource_id, page.day
        ORDER BY page.day DESC, page.datasource_id ASC
    """)
    if datasource_ids is not None:
        count_sql = count_sql.bindparams(bindparam("datasource_ids", expanding=True))
        daily_sql = daily_sql.bindparams(bindparam("datasource_ids", expanding=True))

    total = db.execute(count_sql, params).scalar_one() * days
    rows = db.execute(daily_sql, params).all()
    return [DailyEnergyAggregate(*row) for row in rows], total


def get_latest_hourly(db: Session, datasource_id: int | None = None) -> FactEnergyHourly | None:
    """Get the most recent hourly energy reading."""
    query = db.query(FactEnergyHourly)
    
    if datasource_id:
        query = query.join(
            IngestBatch, FactEnergyHourly.source_batch_id == IngestBatch.batch_id
        ).filter(IngestBatch.datasource_id == datasource_id)
    
    return query.order_by(FactEnergyHourly.ts.desc()).first()


def get_stats(db: Session) -> dict:
    """Get energy data statistics."""
    # Hourly stats
    hourly_stats = db.query(
        func.count(FactEnergyHourly.energy_id).label('count'),
        func.min(FactEnergyHourly.ts).label('first'),
        func.max(FactEnergyHourly.ts).label('last'),
        func.count(func.distinct(FactEnergyHourly.source_device_id)).label('devices')
    ).first()
    
    # Daily stats
    daily_stats = db.query(
        func.count(FactEnergyDaily.energy_id).label('count'),
        func.min(FactEnergyDaily.ts).label('first'),
        func.max(FactEnergyDaily.ts).label('last'),
        func.count(func.distinct(FactEnergyDaily.source_device_id)).label('devices')
    ).first()
    
    return {
        "hourly_count": hourly_stats.count or 0,
        "daily_count": daily_stats.count or 0,
        "hourly_first": hourly_stats.first,
        "hourly_last": hourly_stats.last,
        "daily_first": daily_stats.first,
        "daily_last": daily_stats.last,
        "hourly_devices": hourly_stats.devices or 0,
        "daily_devices": daily_stats.devices or 0,
    }
