from typing import Optional
from pydantic import BaseModel


class Property(BaseModel):
    id: Optional[int] = None
    status: str
    price: Optional[float] = None
    bed: Optional[int] = None
    bath: Optional[float] = None
    acre_lot: Optional[float] = None
    house_size: Optional[float] = None
    price_per_acre: Optional[float] = None
    price_per_sqft: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    zip_code: Optional[int] = None


class PropertyDetail(Property):
    zip_info: Optional[dict] = None


class Demographics(BaseModel):
    zip_code: str
    median_income: Optional[int] = None
    population: Optional[int] = None
    median_age: Optional[float] = None


class PropertiesSearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[Property]
