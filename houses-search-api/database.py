import aiosqlite
import logging
import pandas as pd
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from config import DATABASE_FILE, CSV_URL, DEMOGRAPHICS_CACHE_TTL_HOURS

logger = logging.getLogger(__name__)

DB_FILE = DATABASE_FILE

STATE_MAPPING = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming"
}

REVERSE_STATE_MAPPING = {v: k for k, v in STATE_MAPPING.items()}


async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("PRAGMA synchronous = OFF")
        await db.execute("PRAGMA cache_size = 10000")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                price REAL,
                bed INTEGER,
                bath REAL,
                acre_lot REAL,
                house_size REAL,
                price_per_acre REAL,
                price_per_sqft REAL,
                address TEXT,
                city TEXT,
                state TEXT,
                state_code TEXT,
                zip_code INTEGER
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS zip_cache (
                zip_code TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                cached_at TIMESTAMP NOT NULL
            )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_status ON properties(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_state_code ON properties(state_code)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_zip_code ON properties(zip_code)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_city ON properties(city)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_price ON properties(price)")

        cursor = await db.execute("SELECT COUNT(*) FROM properties")
        count = await cursor.fetchone()

        if count[0] == 0:
            logger.info("Importing properties from CSV...")
            try:
                await _import_csv_data(db)
                await db.commit()
                logger.info("CSV import completed successfully")
            except Exception as e:
                logger.warning(f"Failed to import CSV on startup: {e}. App will run without data.")
                await db.commit()
        else:
            logger.info(f"Database already contains {count[0]} properties, skipping import")


async def _import_csv_data(db: aiosqlite.Connection):
    """Download and import CSV data into the database."""
    try:
        csv_file = "data.csv.cache"

        if Path(csv_file).exists():
            logger.info("Using cached CSV file")
            df = pd.read_csv(csv_file)
        else:
            logger.info("Downloading CSV...")
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(CSV_URL)
                response.raise_for_status()

            with open(csv_file, 'w') as f:
                f.write(response.text)
            logger.info("CSV cached locally")
            df = pd.read_csv(pd.io.common.StringIO(response.text))

        if 'df' not in locals():
            df = pd.read_csv(csv_file)
        logger.info(f"Downloaded CSV with {len(df)} rows")

        df.columns = df.columns.str.lower().str.strip()

        df['state_code'] = df.get('state', '').apply(
            lambda x: REVERSE_STATE_MAPPING.get(str(x).strip(), None) if pd.notna(x) else None
        )

        df['price_per_acre'] = df.apply(
            lambda row: row['price'] / row['acre_lot']
            if pd.notna(row['price']) and pd.notna(row['acre_lot']) and row['acre_lot'] != 0
            else None,
            axis=1
        )

        df['price_per_sqft'] = df.apply(
            lambda row: row['price'] / row['house_size']
            if pd.notna(row['price']) and pd.notna(row['house_size']) and row['house_size'] != 0
            else None,
            axis=1
        )

        columns = [
            'status', 'price', 'bed', 'bath', 'acre_lot', 'house_size',
            'price_per_acre', 'price_per_sqft', 'address', 'city', 'state', 'state_code', 'zip_code'
        ]

        rows = []
        for _, row in df.iterrows():
            rows.append(tuple(row.get(col) for col in columns))
        placeholders = ','.join(['?' for _ in columns])
        await db.executemany(
            f"INSERT INTO properties ({','.join(columns)}) VALUES ({placeholders})",
            rows
        )

        logger.info(f"Inserted {len(df)} properties into database")

    except Exception as e:
        logger.error(f"Failed to import CSV: {e}")
        raise


async def query_properties(
    status: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bed: Optional[int] = None,
    max_bed: Optional[int] = None,
    min_bath: Optional[float] = None,
    max_bath: Optional[float] = None,
    min_acre_lot: Optional[float] = None,
    max_acre_lot: Optional[float] = None,
    min_price_per_acre: Optional[float] = None,
    max_price_per_acre: Optional[float] = None,
    min_house_size: Optional[float] = None,
    max_house_size: Optional[float] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    state_code: Optional[str] = None,
    zip_code: Optional[int] = None,
    zip_codes: Optional[list[int]] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "price",
    sort_order: str = "asc",
) -> tuple[int, list[dict]]:
    """Query properties with dynamic filtering."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        where_clauses = ["status = ?"]
        params = [status]

        if min_price is not None:
            where_clauses.append("price >= ?")
            params.append(min_price)
        if max_price is not None:
            where_clauses.append("price <= ?")
            params.append(max_price)
        if min_bed is not None:
            where_clauses.append("bed >= ?")
            params.append(min_bed)
        if max_bed is not None:
            where_clauses.append("bed <= ?")
            params.append(max_bed)
        if min_bath is not None:
            where_clauses.append("bath >= ?")
            params.append(min_bath)
        if max_bath is not None:
            where_clauses.append("bath <= ?")
            params.append(max_bath)
        if min_acre_lot is not None:
            where_clauses.append("acre_lot >= ?")
            params.append(min_acre_lot)
        if max_acre_lot is not None:
            where_clauses.append("acre_lot <= ?")
            params.append(max_acre_lot)
        if min_price_per_acre is not None:
            where_clauses.append("price_per_acre >= ?")
            params.append(min_price_per_acre)
        if max_price_per_acre is not None:
            where_clauses.append("price_per_acre <= ?")
            params.append(max_price_per_acre)
        if min_house_size is not None:
            where_clauses.append("house_size >= ?")
            params.append(min_house_size)
        if max_house_size is not None:
            where_clauses.append("house_size <= ?")
            params.append(max_house_size)
        if city is not None:
            where_clauses.append("city = ?")
            params.append(city)
        if state is not None:
            where_clauses.append("state = ?")
            params.append(state)
        if state_code is not None:
            where_clauses.append("state_code = ?")
            params.append(state_code)
        if zip_code is not None:
            where_clauses.append("zip_code = ?")
            params.append(zip_code)
        if zip_codes is not None and len(zip_codes) > 0:
            placeholders = ','.join(['?' for _ in zip_codes])
            where_clauses.append(f"zip_code IN ({placeholders})")
            params.extend(zip_codes)

        # Validate sort_by
        valid_sorts = [
            'price', 'bed', 'bath', 'acre_lot', 'house_size', 'price_per_acre',
            'price_per_sqft', 'city', 'state_code', 'zip_code'
        ]
        if sort_by not in valid_sorts:
            sort_by = 'price'

        sort_order = sort_order.upper()
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'ASC'

        # Get total count
        count_query = f"SELECT COUNT(*) FROM properties WHERE {' AND '.join(where_clauses)}"
        cursor = await db.execute(count_query, params)
        total = await cursor.fetchone()
        total = total[0] if total else 0

        # Get paginated results
        offset = (page - 1) * page_size
        query = f"""
            SELECT * FROM properties
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        results = [dict(row) for row in rows]

        return total, results


async def get_property_by_id(property_id: int) -> Optional[dict]:
    """Fetch a single property by ID."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM properties WHERE id = ?",
            [property_id]
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_cached_demographics(zip_code: str) -> Optional[dict]:
    """Get cached demographics data if it exists and is not expired."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT data, cached_at FROM zip_cache WHERE zip_code = ?",
            [zip_code]
        )
        row = await cursor.fetchone()

        if not row:
            return None

        # Check if cache is still valid
        cached_at = datetime.fromisoformat(row['cached_at'])
        if datetime.now() - cached_at > timedelta(hours=DEMOGRAPHICS_CACHE_TTL_HOURS):
            # Cache expired, delete it
            await db.execute("DELETE FROM zip_cache WHERE zip_code = ?", [zip_code])
            await db.commit()
            return None

        import json
        return json.loads(row['data'])


async def cache_demographics(zip_code: str, data: dict):
    """Cache demographics data for a zip code."""
    import json
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO zip_cache (zip_code, data, cached_at)
            VALUES (?, ?, ?)
            """,
            [zip_code, json.dumps(data), datetime.now().isoformat()]
        )
        await db.commit()
