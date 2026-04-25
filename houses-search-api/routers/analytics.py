import sys
from pathlib import Path
from fastapi import APIRouter
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import DB_FILE
import aiosqlite

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/top-cities")
async def top_cities(limit: int = 10):
    """Get top 10 cities by number of listings."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            SELECT city, COUNT(*) as count
            FROM properties
            WHERE city IS NOT NULL
            GROUP BY city
            ORDER BY count DESC
            LIMIT ?
        """, [limit])
        rows = await cursor.fetchall()
        return [{"city": city, "count": count} for city, count in rows]


@router.get("/top-states")
async def top_states(limit: int = 10):
    """Get top 10 states by number of listings."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            SELECT state_code, COUNT(*) as count
            FROM properties
            WHERE state_code IS NOT NULL
            GROUP BY state_code
            ORDER BY count DESC
            LIMIT ?
        """, [limit])
        rows = await cursor.fetchall()
        return [{"state_code": state, "count": count} for state, count in rows]


@router.get("/price-stats")
async def price_stats():
    """Get price statistics across all properties."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            SELECT
                COUNT(*) as total_listings,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(price_per_sqft) as avg_price_per_sqft,
                AVG(price_per_acre) as avg_price_per_acre
            FROM properties
            WHERE price IS NOT NULL
        """)
        row = await cursor.fetchone()
        return {
            "total_listings": row[0],
            "avg_price": round(row[1], 2) if row[1] else None,
            "min_price": row[2],
            "max_price": row[3],
            "avg_price_per_sqft": round(row[4], 2) if row[4] else None,
            "avg_price_per_acre": round(row[5], 2) if row[5] else None,
        }


@router.get("/status-distribution")
async def status_distribution():
    """Get distribution of properties by status."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("""
            SELECT status, COUNT(*) as count
            FROM properties
            GROUP BY status
        """)
        rows = await cursor.fetchall()
        return [{"status": status, "count": count} for status, count in rows]


@router.get("/database-info")
async def database_info():
    """Get database statistics."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM properties")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM zip_cache")
        cached_zips = (await cursor.fetchone())[0]

        return {
            "total_properties": total,
            "cached_demographics": cached_zips,
            "database_file": "houses.db",
        }
