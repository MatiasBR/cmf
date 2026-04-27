# Houses Search API

FastAPI backend service for searching 2.2M+ real estate listings with demographic enrichment and analytics.

## Features

- Property search with 20+ filter combinations
- Demographic data from ZipWho (cached 24h)
- Auto-import of 2.2M listings on startup
- Analytics endpoints (top cities, price stats, distributions)
- Input validation with clear error messages
- Rate limiting (100 req/min per IP, built-in)
- Full test coverage (92 tests, 88%)

## Getting Started

**Requirements:** Python 3.10+

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
./start.sh  # Windows: uvicorn main:app --reload
```

API runs at `http://localhost:8000` (docs at `/docs`)

**Performance:**
- First startup: 8-10s (CSV download + import to SQLite)
- Subsequent: 1-2s (reads from cache)

## Key Features

**Validation:** Invalid params return 422/400 with clear errors. Conflicting filters (e.g., min_price > max_price) are caught at parse time.

**Analytics endpoints:**
```bash
GET /analytics/top-cities              # Top 10 cities
GET /analytics/top-states              # Top 10 states  
GET /analytics/price-stats             # Min/avg/max prices
GET /analytics/status-distribution     # Count by status
GET /analytics/database-info           # Total listings
```

**Rate limiting:** 100 req/min per IP using in-memory tracking. Health checks exempt. Returns 429 when exceeded.

**Production-ready:**
- Startup is idempotent (safe restarts, no duplicates)
- Async throughout (non-blocking DB + HTTP)
- Demographics cached 24h in SQLite
- Bulk inserts (executemany) for speed
- Indexes on status, state_code, zip_code, city, price

## API Endpoints

### Search Properties
```bash
GET /properties?status=for_sale&min_price=200000&max_price=500000&state_code=CA
```

**Parameters (all optional except `status`):**
- `status` (required): `for_sale | sold | ready_to_build`
- Price: `min_price`, `max_price`
- Beds/Baths: `min_bed`, `max_bed`, `min_bath`, `max_bath`
- Size: `min_house_size`, `max_house_size`, `min_acre_lot`, `max_acre_lot`
- Derived: `min_price_per_sqft`, `max_price_per_sqft`, `min_price_per_acre`, `max_price_per_acre`
- Location: `city`, `state`, `state_code`, `zip_code`
- Demographics (requires `state_code`): `min_population`, `max_population`, `min_median_income`, `max_median_income`, `min_median_age`, `max_median_age`
- Pagination: `page` (default: 1), `page_size` (default: 20, max: 100)
- Sorting: `sort_by` (default: price), `sort_order` (default: asc)

**Response:**
```json
{
  "total": 1389306,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": 121781,
      "status": "for_sale",
      "price": null,
      "bed": null,
      "bath": null,
      "state_code": "NY",
      "zip_code": 11237,
      ...
    }
  ]
}
```

### Property Details
```bash
GET /property/121781?include_zip_info=true
```

**Response with demographics:**
```json
{
  "id": 121781,
  "status": "for_sale",
  "city": "Brooklyn",
  "state_code": "NY",
  "zip_code": 11237,
  "zip_info": {
    "median_income": 72728,
    "population": 27202,
    "median_age": 37.2
  }
}
```

### Demographics
```bash
GET /demographics/10001
```

**Response:**
```json
{
  "zip_code": "10001",
  "median_income": 75000,
  "population": 100000,
  "median_age": 35.5
}
```

### Analytics (Bonus Feature)
```bash
GET /analytics/top-cities       # Top 10 cities by listings
GET /analytics/top-states       # Top 10 states by listings
GET /analytics/price-stats      # Average, min, max prices
GET /analytics/status-distribution  # Count by status (for_sale, sold, etc)
GET /analytics/database-info    # Total properties, cached demographics
```

**Example:**
```bash
GET /analytics/price-stats
→ {
    "total_listings": 2226382,
    "avg_price": 345000,
    "min_price": 15000,
    "max_price": 95000000,
    "avg_price_per_sqft": 145.32
  }
```

### Health Check
```bash
GET /health
```

## How It Works

**Startup (first run):**
1. Download CSV from S3 (2.2M rows)
2. Map state names to codes (CA, NY, etc.)
3. Calculate derived fields (price_per_sqft, price_per_acre)
4. Bulk insert into SQLite with indexes
5. Skip on subsequent runs (checks if data exists)

**Demographics:**
- Query ZipWho for each zip code
- Parse HTML (BeautifulSoup), extract income/population/age
- Cache 24 hours in SQLite to avoid repeated requests
- Search by demographic criteria hits ZipWho's demo filter endpoint

**Property search flow:**
1. If demographic filters + state provided: call ZipWho, get matching zips
2. Build SQL WHERE clause with all filters (status, price, beds, etc.)
3. Apply pagination & sort
4. Return results with optional zip demographic data

## Architecture

```
houses-search-api/
├── main.py              # FastAPI app, startup event
├── config.py            # Environment variables
├── database.py          # SQLite async (aiosqlite)
├── scraper.py           # ZipWho HTML parsing
├── models.py            # Pydantic request/response models
├── routers/
│   ├── properties.py    # Search & detail endpoints
│   └── demographics.py  # Demographics endpoint
├── tests/               # 92 tests, 88% coverage
└── houses.db            # SQLite database (auto-created)
```

## Design Notes

**SQLite:** Portable single file, zero external deps, async via aiosqlite. Fast enough for 2.2M rows, though PostgreSQL is better for distributed systems.

**Caching:** 24h TTL balances freshness vs API load. Survives restarts, configurable via .env.

**Idempotent startup:** Checks if data exists before download. Safe to restart, no duplicates, but requires full re-import for data updates.

**Derived fields:** price_per_sqft and price_per_acre calculated at import time. Avoids division-by-zero at runtime, trades ~10% storage.

## Testing

```bash
pytest                    # Run all
pytest --cov=.           # With coverage
pytest tests/test_endpoints.py -v  # Specific file
```

**Coverage:** 92 tests, 88% overall. Gaps in CSV import (startup-only) and ZipWho parsing (HTML fragility).

## Performance

**Startup:**
- First run: 8-10s (CSV download + import)
- Cached CSV: 3-5s (parse + DB insert)
- Subsequent: 1-2s (read from DB)

**Queries:**
- Simple filter: <50ms
- Complex: 100-200ms
- With demographics: 1-2s (includes ZipWho call)
- Cached demographics: <5ms

**Optimizations:**
- Bulk insert (executemany) 10x faster
- Indexes on status, state_code, zip_code, city, price
- SQLite pragma: SYNCHRONOUS=OFF, CACHE_SIZE=10000
- CSV cached locally (skip download)
- Demographics cached 24h

## Environment Variables

```bash
# API
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=Houses Search API
API_VERSION=1.0.0

# Database
DATABASE_FILE=houses.db

# Data source
CSV_URL=https://getgloby-realtor-challenge.s3.us-east-1.amazonaws.com/realtor-data.csv

# Demographics
DEMOGRAPHICS_API_TIMEOUT=10
DEMOGRAPHICS_CACHE_TTL_HOURS=24

# Logging
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=*
```

## Security

- ✅ CSV_URL in `.env` (not hardcoded)
- ✅ `.env` in `.gitignore`
- ✅ SQL queries parameterized (no injection)
- ✅ Input validation with Pydantic
- ✅ CORS configured
- ✅ Graceful error handling

## Error Handling

| Scenario | Response | Behavior |
|----------|----------|----------|
| Invalid property ID | 404 | Returns not found |
| Missing required param | 422 | Validation error |
| ZipWho timeout | 503 | Service unavailable |
| Invalid zip code | 503 | Parse error |
| Conflicting filters | 200 + empty | Returns empty results |

## Database Schema

### properties table
```sql
id INTEGER PRIMARY KEY
status TEXT (for_sale, sold, ready_to_build)
price REAL
bed INTEGER
bath REAL
acre_lot REAL
house_size REAL
price_per_acre REAL (calculated)
price_per_sqft REAL (calculated)
address TEXT
city TEXT
state TEXT (full name: "California")
state_code TEXT (two letters: "CA")
zip_code INTEGER

INDEXES:
- status
- state_code
- zip_code
- city
- price
```

### zip_cache table
```sql
zip_code TEXT PRIMARY KEY
data TEXT (JSON: {"median_income": ..., "population": ..., "median_age": ...})
cached_at TIMESTAMP (24h TTL)
```

## Example Workflows

### Find affordable 3-bed homes in NY with good demographics
```bash
curl "http://localhost:8000/properties?status=for_sale&state_code=NY&min_bed=3&max_bed=3&max_price=400000&min_population=50000&max_population=500000"
```

### Get details + demographics for a specific property
```bash
curl "http://localhost:8000/property/121781?include_zip_info=true"
```

### Find luxury homes in high-income areas
```bash
curl "http://localhost:8000/properties?status=for_sale&state_code=CA&min_price=1000000&state_code=CA&min_median_income=150000"
```

### Search by multiple criteria
```bash
curl "http://localhost:8000/properties?status=for_sale&city=Brooklyn&min_bed=2&max_bed=4&min_bath=1.5&max_bath=3&min_price_per_sqft=150&max_price_per_sqft=400&page_size=50&sort_by=price&sort_order=asc"
```

## Limitations & Future Work

### Current Limitations
1. **HTML Parsing fragile** - ZipWho structure may change
2. **Demographics incomplete** - Only parse 3 fields (median_income, population, median_age)
3. **Territories excluded** - AS, GU, MP, PR, VI not supported (no ZipWho data)

### Future Enhancements
- [ ] Replace ZipWho scraping with US Census API (official, reliable)
- [ ] Add API key authentication for rate limiting
- [ ] Add more demographic fields (education, income distribution)
- [ ] Support schedule-based data refresh
- [ ] Add Elasticsearch for full-text search
- [ ] Implement WebSocket for real-time updates
- [ ] Add property image gallery support
- [ ] ML: Price prediction model
- [ ] Implement Redis caching for high-traffic scenarios

## Deployment

**Docker:**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**systemd (Linux):**
```ini
[Unit]
Description=Houses Search API
After=network.target

[Service]
Type=notify
User=appuser
WorkingDirectory=/opt/houses-api
ExecStart=/opt/houses-api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**Environment:**
```bash
# Production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
DEMOGRAPHICS_CACHE_TTL_HOURS=24
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Change `API_PORT` in .env or kill process: `lsof -i :8000` |
| Database locked | Remove `houses.db` and restart |
| Slow first startup | Normal (2.2M rows). Check internet for CSV download. |
| Tests fail | `pip install -r requirements.txt` && `pytest -v` |
| Import stuck | Check CSV_URL is valid and internet working |
| ZipWho errors | Cache is 24h old. Clear `zip_cache` if data is stale. |

## Tech Stack

- **Python 3.10+** with async/await
- **FastAPI 0.136** for HTTP + OpenAPI docs
- **SQLite + aiosqlite** for async database
- **BeautifulSoup4** for ZipWho HTML parsing
- **pytest** with 92 tests (88% coverage)

## License

MIT
