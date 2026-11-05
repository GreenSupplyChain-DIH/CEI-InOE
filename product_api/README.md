# CEI-InOE Product API

A separate, private FastAPI service that publishes governed **data products** from the edge CEI-InOE
PostgreSQL to a dataspace through the FIWARE Data Space Connector (FDC). It is *not* a replacement for the
operational `api/` service and never shares its routes, models, auth or CORS settings.

See `docs/CEI_INOE_PRODUCT_API_IMPLEMENTATION_BRIEF.md` and `docs/FDC_INFRASTRUCTURE_AND_INSTALLATION.md`.

## Product: `site-energy-consumption-summary` v1

```http
GET /products/v1/site-energy-consumption-summary?site=site-pilot-01&start_date=2026-10-01&end_date=2026-10-31
```

- Daily kWh per calendar day (in the site's reporting timezone), summed from `fact_energy_hourly`.
- `site` is a pseudonymous alias resolved through a secret registry (see below).
- Window: `start_date <= end_date`, at most `PRODUCT_API_MAX_DAYS` (31) days; oversized ranges are rejected (422).
- Unknown query parameters are rejected. Days not yet started are not returned.
- `data_quality`: `complete` (every expected hour present; 23/25 h on DST days), `partial` (+ `coverage_percent`), or
  `missing` (`energy_consumption_kwh: null`). The rule is pending product-owner approval.
- Unknown and not-permitted sites both return `403 Access denied`.
- Status codes: 401 (no/invalid token or client), 403 (context claims missing, purpose or site not allowed),
  422 (validation / window), 429 (rate limit), 503 (database unavailable).

## Layout

```
app/main.py                 app factory, lifespan, audit middleware
app/config.py               PRODUCT_API_* settings and startup guards
app/auth.py                 AuthorisationContext + authenticator selection
app/auth_oidc.py            OIDC/JWT (JWKS) validator - read its docstring for the glossary and usage
app/auth_mock.py            development-only mock
app/routers/                health + products
app/services/               site registry, product assembly, audit + rate limit
app/repositories/           PostgreSQL read access (view only)
app/schemas/product_v1.py   public contract (standalone DTOs)
tests/{unit,integration,contract}
```

## Configuration

Copy `.env.example` to `.env`. All variables are prefixed `PRODUCT_API_`.

**Site registry** (sensitive; mount as a secret, never commit): copy
`app/policies/site_product_registry.example.yaml` to `product_api/site_product_registry.yaml`.
Each datasource has a `ts_timezone`: the timezone in which `fact_energy_hourly.ts` is stored. It is assumed to be
naive Cyprus local time (`Asia/Nicosia`, **to be verified**). After data is migrated to UTC, change it to `UTC`;
no code change is needed.

## Authentication

- `oidc` (default): `Authorization: Bearer <JWT>` validated for signature (JWKS), `iss`, `aud`, `exp`/`nbf`,
  allowed client id, and required participant/purpose/contract claims. Claim names are configurable until the FDC
  token layout is agreed.
- `mock`: development only. Requires `PRODUCT_API_ENV=development`; the app refuses to start otherwise.

```bash
PRODUCT_API_ENV=development PRODUCT_API_AUTH_MODE=mock \
PRODUCT_API_DATABASE_URL=postgresql://product_api_ro:...@localhost:5432/ocei \
PRODUCT_API_SITE_REGISTRY_PATH=./product_api/site_product_registry.yaml \
uvicorn app.main:app --port 8100     # run from product_api/; /docs is enabled only in development
```

The raw CEI-InOE `X-API-Key` is never accepted.

## Database role

Alembic revision `a8b9c0d1e2f3` creates the view `product_energy_hourly_v1` (`ts`, `energy_kwh`, `datasource_id`)
and the login role `product_api_ro` with `SELECT` on that view only:

```bash
PRODUCT_API_DB_PASSWORD='...' alembic upgrade head
```

The password is not stored in the migration; without it the role cannot log in with a password.

## Deploy

```bash
cp product_api/.env.example product_api/.env   # edit
docker compose -f docker-compose.product-api.yml --env-file product_api/.env up -d --build
```

No host port is published. Reach it only from the connector over a private network (see the comments in the
compose file). Audit records are JSON lines on stdout (logger `product_api.audit`).

## Tests

```bash
cd product_api && pip install -r requirements.txt && python -m pytest tests
# Optional PostgreSQL integration test against a disposable database:
PRODUCT_API_TEST_DATABASE_URL=postgresql://user:pw@localhost:5432/db python -m pytest tests/integration
```

## Open items

Verify the `ts` timezone per datasource; agree the FDC token claims/issuer/audience (and whether mTLS is also
required); confirm site aliases, datasource mapping and data-quality rules; set audit retention, revocation target
and incident contacts before external sharing.
