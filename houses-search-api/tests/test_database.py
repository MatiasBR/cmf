import pytest
import sys
from pathlib import Path
import asyncio
import aiosqlite

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    query_properties, get_property_by_id, get_cached_demographics,
    cache_demographics, init_db, STATE_MAPPING, REVERSE_STATE_MAPPING, DB_FILE
)


@pytest.mark.asyncio
class TestDatabaseQueries:
    """Test database query functions."""

    async def test_query_properties_basic(self):
        """Should query properties with status filter."""
        total, results = await query_properties(status="for_sale", page_size=5)
        assert isinstance(total, int)
        assert isinstance(results, list)
        assert len(results) <= 5

    async def test_query_properties_pagination(self):
        """Pagination should work correctly."""
        _, results1 = await query_properties(status="for_sale", page=1, page_size=5)
        _, results2 = await query_properties(status="for_sale", page=2, page_size=5)
        assert len(results1) == 5
        assert len(results2) == 5
        # IDs should be different between pages
        ids1 = [r['id'] for r in results1]
        ids2 = [r['id'] for r in results2]
        assert ids1 != ids2

    async def test_query_properties_with_price_filter(self):
        """Price filters should be applied."""
        _, results = await query_properties(
            status="for_sale",
            min_price=100000,
            max_price=500000,
            page_size=10
        )
        for prop in results:
            if prop['price'] is not None:
                assert 100000 <= prop['price'] <= 500000

    async def test_query_properties_with_bed_filter(self):
        """Bed filter should be applied."""
        _, results = await query_properties(
            status="for_sale",
            min_bed=2,
            max_bed=4,
            page_size=10
        )
        for prop in results:
            if prop['bed'] is not None:
                assert 2 <= prop['bed'] <= 4

    async def test_query_properties_with_state_code(self):
        """State code filter should work."""
        _, results = await query_properties(
            status="for_sale",
            state_code="CA",
            page_size=5
        )
        for prop in results:
            assert prop['state_code'] == "CA"

    async def test_query_properties_with_city(self):
        """City filter should work."""
        # First get a city from results
        _, results = await query_properties(status="for_sale", page_size=1)
        if results and results[0].get('city'):
            city = results[0]['city']
            _, city_results = await query_properties(
                status="for_sale",
                city=city,
                page_size=5
            )
            for prop in city_results:
                if prop['city'] is not None:
                    assert prop['city'] == city

    async def test_query_properties_sorting_asc(self):
        """Sorting ascending should work."""
        _, results = await query_properties(
            status="for_sale",
            sort_by="price",
            sort_order="asc",
            page_size=10
        )
        prices = [r['price'] for r in results if r['price'] is not None]
        assert prices == sorted(prices)

    async def test_query_properties_sorting_desc(self):
        """Sorting descending should work."""
        _, results = await query_properties(
            status="for_sale",
            sort_by="price",
            sort_order="desc",
            page_size=10
        )
        prices = [r['price'] for r in results if r['price'] is not None]
        if len(prices) > 1:
            assert prices == sorted(prices, reverse=True)

    async def test_query_properties_with_zip_code(self):
        """Zip code filter should work."""
        _, results = await query_properties(status="for_sale", page_size=1)
        if results and results[0].get('zip_code'):
            zip_code = results[0]['zip_code']
            _, zip_results = await query_properties(
                status="for_sale",
                zip_code=zip_code,
                page_size=5
            )
            for prop in zip_results:
                if prop['zip_code'] is not None:
                    assert prop['zip_code'] == zip_code

    async def test_get_property_by_id_found(self):
        """Should get property by valid ID."""
        # First get a valid ID
        _, results = await query_properties(status="for_sale", page_size=1)
        if results:
            prop_id = results[0]['id']
            prop = await get_property_by_id(prop_id)
            assert prop is not None
            assert prop['id'] == prop_id

    async def test_get_property_by_id_not_found(self):
        """Should return None for non-existent ID."""
        prop = await get_property_by_id(999999999)
        assert prop is None

    async def test_query_properties_invalid_sort_by(self):
        """Invalid sort_by should use default."""
        _, results = await query_properties(
            status="for_sale",
            sort_by="invalid_column",
            page_size=5
        )
        assert isinstance(results, list)

    async def test_query_properties_all_filters(self):
        """Should handle multiple filters together."""
        _, results = await query_properties(
            status="for_sale",
            min_price=50000,
            max_price=500000,
            min_bed=2,
            max_bed=5,
            state_code="OH",
            page_size=10
        )
        assert isinstance(results, list)
        for prop in results:
            if prop['price'] is not None:
                assert prop['price'] >= 50000
            if prop['bed'] is not None:
                assert prop['bed'] >= 2


@pytest.mark.asyncio
class TestDemographicsCache:
    """Test demographics caching."""

    async def test_cache_and_retrieve(self):
        """Should cache and retrieve demographics."""
        test_zip = "12345"
        test_data = {
            "zip_code": test_zip,
            "median_income": 75000,
            "population": 100000,
            "median_age": 35.5
        }

        # Cache data
        await cache_demographics(test_zip, test_data)

        # Retrieve cached data
        cached = await get_cached_demographics(test_zip)
        assert cached is not None
        assert cached["zip_code"] == test_zip
        assert cached["median_income"] == 75000

    async def test_get_non_existent_cache(self):
        """Should return None for non-cached zip code."""
        cached = await get_cached_demographics("00000-invalid")
        assert cached is None


class TestStateMappings:
    """Test state code mappings."""

    def test_state_mapping_completeness(self):
        """All states should be mapped."""
        assert len(STATE_MAPPING) >= 50  # At least 50 states
        assert "CA" in STATE_MAPPING
        assert "NY" in STATE_MAPPING
        assert "TX" in STATE_MAPPING

    def test_reverse_state_mapping(self):
        """Reverse mapping should work."""
        assert REVERSE_STATE_MAPPING["California"] == "CA"
        assert REVERSE_STATE_MAPPING["New York"] == "NY"
        assert REVERSE_STATE_MAPPING["Texas"] == "TX"

    def test_bidirectional_mapping(self):
        """State mapping should be bidirectional."""
        for code, name in STATE_MAPPING.items():
            assert REVERSE_STATE_MAPPING[name] == code
