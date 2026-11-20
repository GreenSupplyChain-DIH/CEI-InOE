"""
Pydantic Schemas for CEI-InOE

Schemas derived from SQLAlchemy models for API serialization.
Uses ConfigDict(from_attributes=True) to auto-convert from ORM objects.
"""

from datetime import datetime, date
from typing import Optional, Any, Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from shared.models import SiteType


# =============================================================================
# GeoJSON Coordinate Schema
# =============================================================================

class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""
    type: str = Field("Point", pattern=r"^Point$")
    coordinates: list[float] = Field(..., min_length=2, max_length=3,
                                      description="[longitude, latitude] or [longitude, latitude, altitude]")


# =============================================================================
# Site Schemas
# =============================================================================

class SiteBase(BaseModel):
    """Base schema for site."""
    name: str
    location: GeoJSONPoint
    site_type: SiteType
    owner: dict[str, Any] = Field(..., description="Owner details (person or organisation)")
    administrator_email: str = Field(..., description="Email of the site administrator")


class SiteCreate(SiteBase):
    """Schema for creating a site."""
    pass


class SiteRead(SiteBase):
    """Schema for reading a site."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SiteUpdate(BaseModel):
    """Schema for updating a site."""
    name: Optional[str] = None
    location: Optional[GeoJSONPoint] = None
    site_type: Optional[SiteType] = None
    owner: Optional[dict[str, Any]] = None
    administrator_email: Optional[str] = None


# =============================================================================
# Datasource Schemas
# =============================================================================

class DatasourceBase(BaseModel):
    """Base schema for datasource."""
    external_id: str
    source_category: str = Field(..., description="Category: device, file, api, manual")
    data_type: str = Field(..., description="Type: energy, weather, dairy, pv")
    name: Optional[str] = None
    alias: Optional[str] = None
    client: str
    description: Optional[str] = None
    status: str = "active"
    timezone: str = "UTC"
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )
    site_id: Optional[int] = None


class DatasourceCreate(DatasourceBase):
    """Schema for creating a datasource."""
    pass


class DatasourceUpdate(BaseModel):
    """Schema for updating a datasource."""
    name: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    timezone: Optional[str] = None
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )


class DatasourceRead(DatasourceBase):
    """Schema for reading a datasource."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DatasourceTypeCount(BaseModel):
    """Datasource type with count."""
    data_type: str
    count: int


class PurgeResult(BaseModel):
    """Result of a hard-delete (purge) operation on a datasource."""
    datasource_id: int
    rows_deleted: dict[str, int]
    purged_at: datetime


# =============================================================================
# IngestBatch Schemas
# =============================================================================

class IngestBatchBase(BaseModel):
    """Base schema for ingest batch."""
    source_type: str = Field(..., description="Source type: file, api, stream, manual")
    source_name: str
    datasource_id: Optional[int] = None
    granularity: Optional[str] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None


class IngestBatchCreate(IngestBatchBase):
    """Schema for creating an ingest batch."""
    file_sha256: Optional[str] = None
    pipeline_version: str = "1.0"


class IngestBatchRead(IngestBatchBase):
    """Schema for reading an ingest batch."""
    model_config = ConfigDict(from_attributes=True)
    
    batch_id: UUID
    file_sha256: Optional[str] = None
    status: str
    records_loaded: int
    records_failed: int
    execution_time_ms: Optional[int] = None
    validation_status: Optional[str] = None
    quality_score: Optional[float] = None
    pipeline_version: str
    started_at: datetime
    completed_at: Optional[datetime] = None


class IngestBatchSummary(BaseModel):
    """Summary statistics for ingest batches."""
    total_batches: int
    completed: int
    failed: int
    total_records_loaded: int
    total_records_failed: int


# =============================================================================
# Energy Schemas
# =============================================================================

class EnergyHourlyBase(BaseModel):
    """Base schema for hourly energy data."""
    ts: datetime
    energy_kwh: float


class EnergyHourlyRead(EnergyHourlyBase):
    """Schema for reading hourly energy data."""
    model_config = ConfigDict(from_attributes=True)
    
    energy_id: int
    source_type: str
    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    datasource_id: Optional[int] = None
    ingested_at: Optional[datetime] = None


class EnergyDailyBase(BaseModel):
    """Base schema for daily energy data."""
    ts: date
    energy_kwh: float


class EnergyDailyRead(EnergyDailyBase):
    """Schema for reading daily energy data."""
    model_config = ConfigDict(from_attributes=True)
    
    energy_id: int
    source_type: str
    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    datasource_id: Optional[int] = None
    ingested_at: Optional[datetime] = None


class EnergyDailyAggregateRead(BaseModel):
    """Daily consumption calculated from hourly readings."""
    datasource_id: int
    ts: date
    energy_kwh: Optional[float]
    quality: Literal["complete", "partial", "missing"]
    coverage_percent: float


# =============================================================================
# Environmental Metrics Schemas
# =============================================================================

class EnvironmentalMetricsBase(BaseModel):
    """Base schema for environmental metrics."""
    timestamp: datetime
    atm_pressure: Optional[float] = None
    noise_level_db: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pm10: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction_sectors: Optional[float] = None
    wind_angle: Optional[float] = None
    pm2p5: Optional[float] = None


class EnvironmentalMetricsRead(EnvironmentalMetricsBase):
    """Schema for reading environmental metrics."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    source_type: str
    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    datasource_id: Optional[int] = None
    ingested_at: Optional[datetime] = None


class EnvironmentalMetricsDailySummary(BaseModel):
    """Daily summary of environmental metrics."""
    measurement_date: date
    avg_temperature: Optional[float] = None
    min_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    avg_humidity: Optional[float] = None
    avg_pm10: Optional[float] = None
    max_pm10: Optional[float] = None
    avg_pm2p5: Optional[float] = None
    max_pm2p5: Optional[float] = None
    record_count: int


# =============================================================================
# Dairy Production Schemas
# =============================================================================

class DairyProductionBase(BaseModel):
    """Base schema for dairy production."""
    production_date: date
    day_production_per_cow_kg: Optional[float] = None
    number_of_animals: Optional[int] = None
    average_lactation_days: Optional[int] = None
    fed_per_cow_total_kg: Optional[float] = None
    fed_per_cow_water_kg: Optional[float] = None
    feed_efficiency: Optional[float] = None
    rumination_minutes: Optional[int] = None


class DairyProductionRead(DairyProductionBase):
    """Schema for reading dairy production data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    source_type: str
    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    datasource_id: Optional[int] = None
    ingested_at: Optional[datetime] = None


class DairyProductionMonthlySummary(BaseModel):
    """Monthly summary of dairy production."""
    month: date
    days_recorded: int
    avg_production_per_cow_kg: Optional[float] = None
    max_production_per_cow_kg: Optional[float] = None
    min_production_per_cow_kg: Optional[float] = None
    avg_animals: Optional[int] = None
    avg_feed_efficiency: Optional[float] = None


# =============================================================================
# Pipeline & Quality Schemas
# =============================================================================

class PipelineExecutionRead(BaseModel):
    """Schema for reading pipeline execution records."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    batch_id: Optional[UUID] = None
    pipeline_name: str
    stage: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_in: int
    records_out: int
    error_message: Optional[str] = None


class DataQualityCheckRead(BaseModel):
    """Schema for reading data quality check records."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    batch_id: Optional[UUID] = None
    dataset: str
    check_type: str
    check_name: str
    passed: bool
    failed_count: int
    total_count: int
    failure_rate: Optional[float] = None
    checked_at: datetime


# =============================================================================
# Solar/PV Schemas
# =============================================================================

class SolarHourlyBase(BaseModel):
    """Base schema for hourly solar/PV data."""
    ts: datetime
    pv_yield_kwh: Optional[float] = None
    inverter_yield_kwh: Optional[float] = None
    inverter_power_kw: Optional[float] = None
    ongrid_power_kwh: Optional[float] = None
    buy_power_kwh: Optional[float] = None
    use_power_kwh: Optional[float] = None
    self_use_power_kwh: Optional[float] = None
    self_provide_pct: Optional[float] = None
    perpower_ratio: Optional[float] = None
    installed_capacity_kwp: Optional[float] = None
    power_profit: Optional[float] = None
    reduction_total_co2: Optional[float] = None
    reduction_total_coal: Optional[float] = None
    reduction_total_tree: Optional[float] = None


class SolarHourlyRead(SolarHourlyBase):
    """Schema for reading hourly solar/PV data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    source_type: str
    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    datasource_id: Optional[int] = None
    ingested_at: Optional[datetime] = None


class SolarDailyBase(BaseModel):
    """Base schema for daily solar/PV data."""
    ts: date
    pv_yield_kwh: Optional[float] = None
    inverter_yield_kwh: Optional[float] = None
    inverter_power_kw: Optional[float] = None
    ongrid_power_kwh: Optional[float] = None
    buy_power_kwh: Optional[float] = None
    use_power_kwh: Optional[float] = None
    self_use_power_kwh: Optional[float] = None
    self_provide_pct: Optional[float] = None
    perpower_ratio: Optional[float] = None
    installed_capacity_kwp: Optional[float] = None
    power_profit: Optional[float] = None
    reduction_total_co2: Optional[float] = None
    reduction_total_coal: Optional[float] = None
    reduction_total_tree: Optional[float] = None


class SolarDailyRead(SolarDailyBase):
    """Schema for reading daily solar/PV data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    source_type: str
    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    datasource_id: Optional[int] = None
    ingested_at: Optional[datetime] = None


class SolarMonthlyBase(BaseModel):
    """Base schema for monthly solar/PV data."""
    ts: date
    pv_yield_kwh: Optional[float] = None
    inverter_yield_kwh: Optional[float] = None
    inverter_power_kw: Optional[float] = None
    ongrid_power_kwh: Optional[float] = None
    buy_power_kwh: Optional[float] = None
    use_power_kwh: Optional[float] = None
    self_use_power_kwh: Optional[float] = None
    self_provide_pct: Optional[float] = None
    perpower_ratio: Optional[float] = None
    installed_capacity_kwp: Optional[float] = None
    power_profit: Optional[float] = None
    reduction_total_co2: Optional[float] = None
    reduction_total_coal: Optional[float] = None
    reduction_total_tree: Optional[float] = None


class SolarMonthlyRead(SolarMonthlyBase):
    """Schema for reading monthly solar/PV data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    source_type: str
    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    datasource_id: Optional[int] = None
    ingested_at: Optional[datetime] = None


# =============================================================================
# Weather Forecast Schemas
# =============================================================================

class WeatherForecastRead(BaseModel):
    """Schema for reading weather forecast records."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    forecast_run_at: datetime
    valid_at: datetime
    horizon_hours: int
    site_id: int

    shortwave_radiation_wm2: Optional[float] = None
    direct_radiation_wm2: Optional[float] = None
    direct_normal_irradiance_wm2: Optional[float] = None
    diffuse_radiation_wm2: Optional[float] = None
    global_tilted_irradiance_wm2: Optional[float] = None

    cloud_cover_pct: Optional[float] = None
    cloud_cover_low_pct: Optional[float] = None
    cloud_cover_mid_pct: Optional[float] = None
    cloud_cover_high_pct: Optional[float] = None

    temperature_2m_c: Optional[float] = None
    wind_speed_10m_ms: Optional[float] = None
    wind_direction_10m_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    weather_code: Optional[int] = None
    sunshine_duration_s: Optional[float] = None
    is_day: Optional[bool] = None
    model_id: Optional[str] = None

    source_batch_id: Optional[UUID] = None
    source_device_id: Optional[str] = None
    ingested_at: Optional[datetime] = None


# =============================================================================
# Common Response Schemas
# =============================================================================

class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    data: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedEnergyDailyAggregateResponse(PaginatedResponse):
    """Paginated daily energy aggregates."""
    data: list[EnergyDailyAggregateRead]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: bool
    timestamp: datetime


# =============================================================================
# Data Upload Schemas
# =============================================================================

class DataUploadRequest(BaseModel):
    """Schema for data upload form submission (non-file fields)."""
    field1: Optional[str] = Field(None, description="Placeholder field 1")
    field2: Optional[str] = Field(None, description="Placeholder field 2")


class DataUploadResponse(BaseModel):
    """Response after successful data upload."""
    success: bool
    message: str
    batch_id: Optional[UUID] = None
    filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    fields: Optional[dict[str, Any]] = None


# =============================================================================
# Truck Milk Delivery Schemas
# =============================================================================

class TruckMilkDeliveryBase(BaseModel):
    reception_date: date = Field(..., description="Date milk was received (DD/MM/YYYY)")
    truck_id: str = Field(..., min_length=1, max_length=64, description="Truck / vehicle identifier")
    receipt_number: str = Field(..., min_length=1, max_length=64, description="Receipt number from records")
    farm_of_origin: str = Field(..., min_length=1, max_length=255, description="Name / identifier of the originating farm")
    cow_milk_delivered_kg: float = Field(..., gt=0, description="Cow's milk delivered by this trip (kg)")
    total_cow_milk_in_truck_kg: float = Field(..., gt=0, description="Total cow's milk in truck (kg)")
    total_milk_in_truck_kg: float = Field(..., gt=0, description="Total milk in truck (all species) (kg)")
    silo_number: int = Field(..., ge=0, le=3, description="Silo where milk was stored (0 for Other, 1, 2, or 3)")
    production_batch_numbers: Optional[str] = Field(None, description="Comma-separated production batch number(s)")
    batch_produced_date: Optional[date] = Field(None, description="Date the production batch was produced")


class TruckMilkDeliveryCreate(TruckMilkDeliveryBase):
    pass


class TruckMilkDeliveryUpdate(BaseModel):
    reception_date: Optional[date] = None
    truck_id: Optional[str] = Field(None, min_length=1, max_length=64)
    receipt_number: Optional[str] = Field(None, min_length=1, max_length=64)
    farm_of_origin: Optional[str] = Field(None, min_length=1, max_length=255)
    cow_milk_delivered_kg: Optional[float] = Field(None, gt=0)
    total_cow_milk_in_truck_kg: Optional[float] = Field(None, gt=0)
    total_milk_in_truck_kg: Optional[float] = Field(None, gt=0)
    silo_number: Optional[int] = Field(None, ge=1, le=2)
    production_batch_numbers: Optional[str] = None
    batch_produced_date: Optional[date] = None


class TruckMilkDeliveryRead(TruckMilkDeliveryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# =============================================================================
# API Principal Schemas
# =============================================================================

class ApiPrincipalBase(BaseModel):
    """Base schema for an API principal."""
    name: str
    description: Optional[str] = None
    status: str = "active"
    is_superuser: bool = False


class ApiPrincipalCreate(ApiPrincipalBase):
    """Schema for creating a principal."""
    pass


class ApiPrincipalUpdate(BaseModel):
    """Schema for updating a principal."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ApiPrincipalRead(ApiPrincipalBase):
    """Schema for reading a principal (never includes the API key)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApiPrincipalCreateResponse(ApiPrincipalRead):
    """Returned only once, at creation time, with the plaintext API key."""
    api_key: str = Field(..., description="Plaintext API key - shown only once, store it securely")


class DatasourceAccessGrant(BaseModel):
    """Request body for granting datasource access to a principal."""
    datasource_id: int


class DatasourceAccessRead(BaseModel):
    """A single datasource access grant."""
    model_config = ConfigDict(from_attributes=True)

    datasource_id: int
    granted_at: Optional[datetime] = None
    granted_by: Optional[int] = None
