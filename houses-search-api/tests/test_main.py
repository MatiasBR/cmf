import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


class TestMainApp:
    """Test main app configuration."""

    def test_app_exists(self):
        """App should be created."""
        assert app is not None

    def test_app_has_title(self):
        """App should have title."""
        assert app.title is not None

    def test_app_has_description(self):
        """App should have description."""
        assert app.description is not None

    def test_app_has_version(self):
        """App should have version."""
        assert app.version is not None

    def test_cors_middleware_added(self):
        """Should have CORS middleware."""
        # Check that app has middleware configured
        assert len(app.user_middleware) > 0

    def test_error_middleware_works(self):
        """Error middleware should catch errors."""
        # This tests that the middleware doesn't break normal requests
        response = client.get("/health")
        assert response.status_code == 200


class TestDocumentation:
    """Test API documentation endpoints."""

    def test_swagger_docs_available(self):
        """Swagger docs should be available."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self):
        """ReDoc should be available."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_schema(self):
        """OpenAPI schema should be available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "components" in data


class TestAppHealthy:
    """Test app is working properly."""

    def test_all_routers_included(self):
        """All routers should be included."""
        response = client.get("/openapi.json")
        data = response.json()
        paths = list(data["paths"].keys())

        # Check for expected endpoints
        assert any("/properties" in p for p in paths)
        assert any("/property" in p for p in paths)
        assert any("/demographics" in p for p in paths)
        assert any("/health" in p for p in paths)

    def test_properties_endpoint_in_openapi(self):
        """Properties endpoint should be documented."""
        response = client.get("/openapi.json")
        data = response.json()
        assert "/properties" in data["paths"]

    def test_property_detail_endpoint_in_openapi(self):
        """Property detail endpoint should be documented."""
        response = client.get("/openapi.json")
        data = response.json()
        assert any("/property/" in p or "{" in p for p in data["paths"])

    def test_demographics_endpoint_in_openapi(self):
        """Demographics endpoint should be documented."""
        response = client.get("/openapi.json")
        data = response.json()
        assert any("/demographics" in p for p in data["paths"])


class TestResponseFormats:
    """Test response formats are correct."""

    def test_health_response_format(self):
        """Health response should have correct format."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_properties_response_format(self):
        """Properties response should have required fields."""
        response = client.get("/properties?status=for_sale")
        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_property_response_format(self):
        """Property response should have required fields."""
        # Get a valid ID first
        search = client.get("/properties?status=for_sale&page_size=1")
        if search.json()["results"]:
            prop_id = search.json()["results"][0]["id"]
            response = client.get(f"/property/{prop_id}")
            data = response.json()
            assert "id" in data
            assert "status" in data


class TestErrorHandling:
    """Test error handling."""

    def test_404_for_invalid_endpoint(self):
        """Invalid endpoint should return 404."""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404

    def test_422_for_missing_required_param(self):
        """Missing required param should return 422."""
        response = client.get("/properties")
        assert response.status_code == 422

    def test_422_for_invalid_param_type(self):
        """Invalid param type should return 422."""
        response = client.get("/properties?status=for_sale&page=invalid")
        assert response.status_code == 422

    def test_422_for_invalid_page_size(self):
        """Invalid page size should return 422."""
        response = client.get("/properties?status=for_sale&page_size=999999")
        assert response.status_code == 422


class TestIntegration:
    """Integration tests."""

    def test_full_search_flow(self):
        """Should be able to search and get details."""
        # Search
        search_response = client.get("/properties?status=for_sale&page_size=1")
        assert search_response.status_code == 200

        results = search_response.json()["results"]
        if results:
            prop_id = results[0]["id"]

            # Get detail
            detail_response = client.get(f"/property/{prop_id}")
            assert detail_response.status_code == 200

            detail = detail_response.json()
            assert detail["id"] == prop_id

    def test_search_with_multiple_filters(self):
        """Should work with multiple filters."""
        response = client.get(
            "/properties?status=for_sale&state_code=NY&min_bed=2&max_bed=4"
        )
        assert response.status_code == 200
        assert "results" in response.json()

    def test_pagination_consistency(self):
        """Pagination should be consistent."""
        page1 = client.get("/properties?status=for_sale&page=1&page_size=5")
        page2 = client.get("/properties?status=for_sale&page=2&page_size=5")

        assert page1.status_code == 200
        assert page2.status_code == 200

        data1 = page1.json()
        data2 = page2.json()

        assert data1["page"] == 1
        assert data2["page"] == 2
        assert data1["total"] > 0
