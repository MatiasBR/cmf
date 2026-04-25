from fastapi import APIRouter, HTTPException
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Demographics
from scraper import get_demographics_by_zip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["demographics"])


@router.get("/demographics/{zip_code}", response_model=Demographics)
async def get_demographics(zip_code: str):
    """
    Get demographic information for a zip code.
    Returns 404 if zip code not found.
    Returns 503 if scraping failed.
    """
    data = await get_demographics_by_zip(zip_code)

    if data is None:
        # Could not fetch or parse - check if it's a "not found" vs scraping error
        raise HTTPException(
            status_code=503,
            detail="Unable to fetch demographics data. Service may be temporarily unavailable."
        )

    # If we got here, data should have all fields
    return Demographics(**data)
