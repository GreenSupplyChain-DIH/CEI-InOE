"""OpenAPI contract: the public schema must not drift silently."""

from app.config import Settings
from app.main import create_app


def _schema():
    app = create_app(Settings(env="development", auth_mode="mock", database_url="x"))
    return app.openapi()


def test_only_the_daily_product_is_exposed():
    paths = {p for p in _schema()["paths"] if p.startswith("/products")}
    assert paths == {"/products/v1/site-energy-consumption-summary"}


def test_query_parameters_are_exactly_the_contract():
    op = _schema()["paths"]["/products/v1/site-energy-consumption-summary"]["get"]
    assert {p["name"] for p in op["parameters"]} == {"site", "start_date", "end_date"}


def test_response_schema_fields():
    schemas = _schema()["components"]["schemas"]
    assert set(schemas["SiteEnergySummary"]["properties"]) == {
        "product_id", "product_version", "site", "period", "granularity",
        "timezone", "generated_at", "data",
    }
    assert set(schemas["DailyEnergy"]["properties"]) == {
        "date", "energy_consumption_kwh", "data_quality", "coverage_percent",
    }
