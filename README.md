# CEI-InOE

> **Data ingestion and analytics edge platform** — part of the [O-CEI](https://o-cei.eu/) project.

CEI-InOE collects energy consumption, environmental sensor data, weather forecasts, solar PV generation, and dairy production data from multiple external sources, runs ETL pipelines to validate and load data into a PostgreSQL data warehouse, and exposes the results through a REST API.

---

## Architecture

| Service | Description |
|---------|-------------|
| **`ingestor/`** | Pulls from external APIs (Tago.io, Airbeld, FusionSolar, Open-Meteo) and watches `/data/incoming` for CSV/XLSX files, including Delaval dairy exports; runs concurrent ETL pipelines via a thread worker pool |
| **`api/`** | Read-only FastAPI service; all endpoints protected with `X-API-Key` |
| **`shared/`** | Editable Python package with SQLAlchemy models and Pydantic v2 schemas shared by both services |
| **`alembic/`** | Database migrations |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (local dev only)
- PostgreSQL 16 (provided via Docker)

### Run with Docker (recommended)

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your API credentials

# Start all services
docker-compose -f docker-compose.new.yaml up -d
```

Services started:
| Service | Port |
|---------|------|
| PostgreSQL | 5432 |
| API | 8000 |
| Grafana | 3000 |

### Local Development

```bash
# 1. Install the shared package (required by both services)
pip install -e ./shared

# 2. Run the API
cd api
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Run the Ingestor (separate terminal)
cd ingestor
pip install -r requirements.txt
python app/main.py
```

### Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Generate a migration after changing shared/src/shared/models.py
alembic revision --autogenerate -m "short_description"

# Roll back one step
alembic downgrade -1
```

---

## API

Base URL: `http://localhost:8000`

Authentication: `X-API-Key: <API_KEY>` header on all `/api/v1/*` routes.

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service health (public) |
| `GET /ready` | Readiness probe (public) |
| `GET /api/v1/energy/hourly` | Hourly energy consumption |
| `GET /api/v1/energy/daily` | Daily energy consumption aggregated from hourly readings for online datasources |
| `GET /api/v1/energy/latest` | Latest energy reading |
| `GET /api/v1/energy/stats` | Energy data statistics |
| `GET /api/v1/environmental/hourly` | Environmental sensor readings |
| `GET /api/v1/environmental/latest` | Latest environmental reading |
| `GET /api/v1/environmental/stats` | Environmental statistics |
| `GET /api/v1/forecast/latest` | Latest forecast run as hourly forecast slots |
| `GET /api/v1/forecast/history` | Forecast records filtered by valid-time window |
| `GET /api/v1/dairy/daily` | Daily dairy production records |
| `GET /api/v1/dairy/latest` | Latest dairy production record |
| `GET /api/v1/dairy/stats` | Dairy statistics |
| `GET /api/v1/datasources` | List datasources (devices, files, APIs) |
| `GET /api/v1/datasources/{id}` | Datasource by ID |
| `GET /api/v1/batches` | List ingestion batches |
| `GET /api/v1/batches/{batch_id}` | Batch by UUID |

Interactive docs: **http://localhost:8000/docs** (Swagger UI)

The daily energy endpoint returns datasource/day aggregates, including missing
days, rather than stored daily records. It accepts inclusive date ranges of at
most 366 days and an optional `datasource_id`. Coverage is based on 24 distinct
stored clock-hour buckets, without timezone conversion or DST adjustment.

---

## Configuration

Copy `.env.example` to `.env` and fill in values. Key variables:

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | API | PostgreSQL DSN (`postgresql://user:pass@host:5432/db`) |
| `DB_DSN` | Ingestor | PostgreSQL DSN |
| `API_KEY` | API | `X-API-Key` value for all data endpoints |
| `TAGO_ENABLED` | Ingestor | Enable/disable Tago.io connector (`true`/`false`) |
| `AIRBELD_EMAIL` | Ingestor | Airbeld account email |
| `AIRBELD_PASSWORD` | Ingestor | Airbeld account password |
| `AIRBELD_API_URL` | Ingestor | Airbeld base URL |
| `FUSIONSOLAR_ENABLED` | Ingestor | Enable/disable FusionSolar connector |
| `FUSIONSOLAR_USER` | Ingestor | FusionSolar username |
| `FUSIONSOLAR_SYSTEM_CODE` | Ingestor | FusionSolar system code |
| `OPEN_METEO_ENABLED` | Ingestor | Enable/disable Open-Meteo weather forecast connector |
| `NUM_WORKERS` | Ingestor | Worker thread count (default: `2`) |
| `CORS_ORIGINS` | API | Comma-separated allowed CORS origins |

> ⚠️ Never commit `.env` to version control. Use `.env.example` as the template.

---

## Documentation

You can find more details documentation on the project [wiki](https://github.com/fedjo/CEI-InOE/wiki).

---

## License

This project is developed as part of the [O-CEI](https://o-cei.eu/) project and is licences under [EUPL](https://eupl.eu/).
