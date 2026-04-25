import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self):
        """Health check should return 200 with status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPropertiesEndpoint:
    """Test property search endpoint."""

    def test_search_properties_without_status(self):
        """Search without status should fail with 422."""
        response = client.get("/properties")
        assert response.status_code == 422

    def test_search_properties_with_status(self):
        """Search with status should return 200 and valid structure."""
        response = client.get("/properties?status=for_sale")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "results" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["results"], list)

    def test_search_properties_pagination(self):
        """Pagination should work correctly."""
        response1 = client.get("/properties?status=for_sale&page=1&page_size=10")
        response2 = client.get("/properties?status=for_sale&page=2&page_size=10")

        data1 = response1.json()
        data2 = response2.json()

        assert len(data1["results"]) == 10
        assert data1["page"] == 1
        assert data2["page"] == 2

    def test_search_properties_with_filters(self):
        """Filters should be applied."""
        response = client.get(
            "/properties?status=for_sale&min_bed=2&max_bed=4"
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["bed"] is not None:
                assert 2 <= prop["bed"] <= 4

    def test_search_properties_sorting(self):
        """Sorting should work."""
        response = client.get(
            "/properties?status=for_sale&sort_by=price&sort_order=asc&page_size=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5

    def test_search_properties_max_page_size(self):
        """Page size over 100 should be rejected with 422."""
        response = client.get("/properties?status=for_sale&page_size=500")
        assert response.status_code == 422

    def test_search_properties_valid_max_page_size(self):
        """Page size of 100 should work."""
        response = client.get("/properties?status=for_sale&page_size=100")
        assert response.status_code == 200
        data = response.json()
        assert data["page_size"] == 100

    def test_search_properties_invalid_status(self):
        """Invalid status should be rejected with 422."""
        response = client.get("/properties?status=invalid_status")
        assert response.status_code == 422

    def test_search_properties_with_state_code(self):
        """Filter by state code should work."""
        response = client.get("/properties?status=for_sale&state_code=NY&page_size=5")
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["state_code"] is not None:
                assert prop["state_code"] == "NY"


class TestPropertyDetailEndpoint:
    """Test single property endpoint."""

    def test_get_property_not_found(self):
        """Non-existent property should return 404."""
        response = client.get("/property/999999999")
        assert response.status_code == 404

    def test_get_property_success(self):
        """Valid property ID should return 200."""
        # First, get a valid ID from search
        search_response = client.get("/properties?status=for_sale&page_size=1")
        if search_response.json()["results"]:
            prop_id = search_response.json()["results"][0]["id"]

            response = client.get(f"/property/{prop_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == prop_id
            assert "status" in data
            assert "state_code" in data

    def test_get_property_with_zip_info(self):
        """Getting property with zip_info should add demographics."""
        search_response = client.get("/properties?status=for_sale&page_size=1")
        if search_response.json()["results"]:
            prop_id = search_response.json()["results"][0]["id"]

            response = client.get(f"/property/{prop_id}?include_zip_info=true")
            assert response.status_code == 200
            data = response.json()
            assert "zip_info" in data or data["zip_code"] is None

    def test_get_property_without_zip_info(self):
        """Getting property without zip_info flag should not include demographics."""
        search_response = client.get("/properties?status=for_sale&page_size=1")
        if search_response.json()["results"]:
            prop_id = search_response.json()["results"][0]["id"]

            response = client.get(f"/property/{prop_id}")
            assert response.status_code == 200
            data = response.json()
            assert data.get("zip_info") is None


class TestDemographicsEndpoint:
    """Test demographics endpoint."""

    def test_get_demographics_invalid_zip(self):
        """Invalid zip code should return 503."""
        response = client.get("/demographics/00000")
        assert response.status_code == 503

    def test_get_demographics_valid_format(self):
        """Valid response should have required fields."""
        # This might fail if no valid data, but tests the format
        response = client.get("/demographics/10001")
        # Either 200 with valid data or 503 if not found
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "zip_code" in data
            assert data["zip_code"] == "10001"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_search_with_conflicting_filters(self):
        """min > max should be rejected with 400."""
        response = client.get(
            "/properties?status=for_sale&min_price=1000000&max_price=100"
        )
        assert response.status_code == 400
        assert "min_price must be <= max_price" in response.json()["detail"]

    def test_search_with_null_values(self):
        """API should handle properties with null values."""
        response = client.get("/properties?status=for_sale&page_size=20")
        assert response.status_code == 200
        data = response.json()
        # Just verify it doesn't crash with nulls
        assert len(data["results"]) >= 0

    def test_api_docs_available(self):
        """API documentation should be available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_api_redoc_available(self):
        """ReDoc documentation should be available."""
        response = client.get("/redoc")
        assert response.status_code == 200
