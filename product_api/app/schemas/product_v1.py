"""Public contract for product ``site-energy-consumption-summary`` v1.

These models are the *only* thing returned to consumers. They are standalone
(no ``from_attributes``/ORM coupling) so a new database column can never leak
into the contract. A breaking change must be published as ``/products/v2``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PRODUCT_ID = "site-energy-consumption-summary"
PRODUCT_VERSION = "1.0"

DataQuality = Literal["complete", "partial", "missing"]


class SiteEnergyQuery(BaseModel):
    """Query parameters. Unknown parameters (fields, device ids...) are rejected."""

    model_config = ConfigDict(extra="forbid")

    site: str = Field(
        pattern=r"^[a-z0-9][a-z0-9-]{2,63}$",
        description="Pseudonymous product-site alias",
    )
    start_date: date = Field(description="Start date (inclusive)")
    end_date: date = Field(description="End date (inclusive)")

    @model_validator(mode="after")
    def _ordered(self) -> "SiteEnergyQuery":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


class Period(BaseModel):
    start_date: date
    end_date: date


class DailyEnergy(BaseModel):
    date: date
    energy_consumption_kwh: float | None = Field(
        description="Sum of available hourly readings; null when the day has no data"
    )
    data_quality: DataQuality
    coverage_percent: float = Field(ge=0, le=100)


class SiteEnergySummary(BaseModel):
    product_id: Literal["site-energy-consumption-summary"] = PRODUCT_ID
    product_version: str = PRODUCT_VERSION
    site: str
    period: Period
    granularity: Literal["daily"] = "daily"
    timezone: str = Field(description="IANA timezone used to define the calendar day")
    generated_at: datetime
    data: list[DailyEnergy]
