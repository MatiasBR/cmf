from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Literal
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Property, PropertyDetail, PropertiesSearchResponse
from database import query_properties, get_property_by_id
from scraper import get_demographics_by_zip, search_zips_by_demographics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["properties"])


@router.get("/properties", response_model=PropertiesSearchResponse)
async def search_properties(
    status: Literal["for_sale", "sold", "ready_to_build"] = Query(...),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_bed: Optional[int] = Query(None, ge=0),
    max_bed: Optional[int] = Query(None, ge=0),
    min_bath: Optional[float] = Query(None, ge=0),
    max_bath: Optional[float] = Query(None, ge=0),
    min_acre_lot: Optional[float] = Query(None, ge=0),
    max_acre_lot: Optional[float] = Query(None, ge=0),
    min_price_per_acre: Optional[float] = Query(None, ge=0),
    max_price_per_acre: Optional[float] = Query(None, ge=0),
    min_house_size: Optional[float] = Query(None, ge=0),
    max_house_size: Optional[float] = Query(None, ge=0),
    min_price_per_sqft: Optional[float] = Query(None, ge=0),
    max_price_per_sqft: Optional[float] = Query(None, ge=0),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    state_code: Optional[str] = Query(None),
    zip_code: Optional[int] = Query(None),
    min_population: Optional[int] = Query(None, ge=0),
    max_population: Optional[int] = Query(None, ge=0),
    min_median_income: Optional[int] = Query(None, ge=0),
    max_median_income: Optional[int] = Query(None, ge=0),
    min_median_age: Optional[float] = Query(None, ge=0),
    max_median_age: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Literal["price", "bed", "bath", "acre_lot", "house_size", "state_code", "zip_code"] = Query("price"),
    sort_order: Literal["asc", "desc"] = Query("asc"),
):
    """
    Search for properties with optional filters.
    If demographic filters are provided along with state_code,
    will first search for matching zip codes then filter properties.
    """
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price must be <= max_price")
    if min_bed is not None and max_bed is not None and min_bed > max_bed:
        raise HTTPException(status_code=400, detail="min_bed must be <= max_bed")
    if min_bath is not None and max_bath is not None and min_bath > max_bath:
        raise HTTPException(status_code=400, detail="min_bath must be <= max_bath")
    if min_house_size is not None and max_house_size is not None and min_house_size > max_house_size:
        raise HTTPException(status_code=400, detail="min_house_size must be <= max_house_size")
    if min_population is not None and max_population is not None and min_population > max_population:
        raise HTTPException(status_code=400, detail="min_population must be <= max_population")
    if min_median_income is not None and max_median_income is not None and min_median_income > max_median_income:
        raise HTTPException(status_code=400, detail="min_median_income must be <= max_median_income")

    zip_codes = None

    has_demo_filters = any([
        min_population is not None,
        max_population is not None,
        min_median_income is not None,
        max_median_income is not None,
        min_median_age is not None,
        max_median_age is not None
    ])

    if has_demo_filters and state_code:
        logger.info(f"Searching for zip codes matching demographics in {state_code}")
        zip_codes = await search_zips_by_demographics(
            state_code=state_code,
            min_population=min_population or 0,
            max_population=max_population or 999999,
            min_median_income=min_median_income or 0,
            max_median_income=max_median_income or 999999,
            min_median_age=min_median_age or 0,
            max_median_age=max_median_age or 999
        )

        if not zip_codes:
            # No matching zip codes found
            return PropertiesSearchResponse(
                total=0,
                page=page,
                page_size=page_size,
                results=[]
            )

    # Query properties
    total, results = await query_properties(
        status=status,
        min_price=min_price,
        max_price=max_price,
        min_bed=min_bed,
        max_bed=max_bed,
        min_bath=min_bath,
        max_bath=max_bath,
        min_acre_lot=min_acre_lot,
        max_acre_lot=max_acre_lot,
        min_price_per_acre=min_price_per_acre,
        max_price_per_acre=max_price_per_acre,
        min_house_size=min_house_size,
        max_house_size=max_house_size,
        city=city,
        state=state,
        state_code=state_code,
        zip_code=zip_code,
        zip_codes=zip_codes,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    properties = [Property(**result) for result in results]

    return PropertiesSearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=properties
    )


@router.get("/property/{property_id}", response_model=PropertyDetail)
async def get_property(
    property_id: int,
    include_zip_info: bool = Query(False)
):
    """
    Get a specific property by ID.
    If include_zip_info=true, includes demographic data for the property's zip code.
    """
    prop = await get_property_by_id(property_id)

    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    property_detail = PropertyDetail(**prop)

    # Fetch zip info if requested
    if include_zip_info and prop.get('zip_code'):
        zip_info = await get_demographics_by_zip(str(prop['zip_code']))
        if zip_info:
            property_detail.zip_info = {
                "median_income": zip_info.get("median_income"),
                "population": zip_info.get("population"),
                "median_age": zip_info.get("median_age")
            }

    return property_detail
