import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Property, PropertyDetail, Demographics, PropertiesSearchResponse
from pydantic import ValidationError


class TestPropertyModel:
    """Test Property model."""

    def test_property_creation(self):
        """Should create valid property."""
        prop = Property(
            id=1,
            status="for_sale",
            price=500000,
            bed=3,
            bath=2,
            state_code="NY"
        )
        assert prop.id == 1
        assert prop.status == "for_sale"
        assert prop.price == 500000

    def test_property_with_nulls(self):
        """Should handle null values."""
        prop = Property(
            status="for_sale",
            price=None,
            bed=None
        )
        assert prop.price is None
        assert prop.bed is None

    def test_property_all_fields(self):
        """Should accept all fields."""
        prop = Property(
            id=1,
            status="for_sale",
            price=500000,
            bed=3,
            bath=2,
            acre_lot=0.5,
            house_size=2000,
            price_per_acre=1000000,
            price_per_sqft=250,
            address="123 Main St",
            city="New York",
            state="New York",
            state_code="NY",
            zip_code=10001
        )
        assert prop.address == "123 Main St"
        assert prop.zip_code == 10001


class TestPropertyDetailModel:
    """Test PropertyDetail model."""

    def test_property_detail_without_zip_info(self):
        """Should work without zip_info."""
        detail = PropertyDetail(
            status="for_sale",
            price=500000,
            state_code="NY"
        )
        assert detail.zip_info is None

    def test_property_detail_with_zip_info(self):
        """Should include zip_info when provided."""
        detail = PropertyDetail(
            status="for_sale",
            price=500000,
            state_code="NY",
            zip_info={
                "median_income": 75000,
                "population": 100000,
                "median_age": 35.5
            }
        )
        assert detail.zip_info is not None
        assert detail.zip_info["median_income"] == 75000


class TestDemographicsModel:
    """Test Demographics model."""

    def test_demographics_creation(self):
        """Should create valid demographics."""
        demo = Demographics(
            zip_code="10001",
            median_income=75000,
            population=100000,
            median_age=35.5
        )
        assert demo.zip_code == "10001"
        assert demo.median_income == 75000

    def test_demographics_with_nulls(self):
        """Should handle null demographic values."""
        demo = Demographics(
            zip_code="10001",
            median_income=None,
            population=None,
            median_age=None
        )
        assert demo.zip_code == "10001"
        assert demo.median_income is None


class TestPropertiesSearchResponseModel:
    """Test PropertiesSearchResponse model."""

    def test_search_response_creation(self):
        """Should create valid search response."""
        props = [
            Property(status="for_sale", price=500000),
            Property(status="for_sale", price=600000)
        ]
        response = PropertiesSearchResponse(
            total=100,
            page=1,
            page_size=20,
            results=props
        )
        assert response.total == 100
        assert response.page == 1
        assert len(response.results) == 2

    def test_search_response_empty(self):
        """Should handle empty results."""
        response = PropertiesSearchResponse(
            total=0,
            page=1,
            page_size=20,
            results=[]
        )
        assert response.total == 0
        assert len(response.results) == 0
