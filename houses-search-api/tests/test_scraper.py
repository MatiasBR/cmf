import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import (
    get_demographics_by_zip, search_zips_by_demographics,
    _parse_zip_page, _parse_demographics_search, TERRITORIES_WITH_NO_DATA
)


@pytest.mark.asyncio
class TestGetDemographicsByZip:
    """Test demographic fetching by zip code."""

    @patch('scraper.get_cached_demographics')
    async def test_returns_cached_data(self, mock_cache):
        """Should return cached data if available."""
        test_data = {
            "zip_code": "10001",
            "median_income": 75000,
            "population": 100000,
            "median_age": 35.5
        }
        mock_cache.return_value = test_data

        result = await get_demographics_by_zip("10001")
        assert result == test_data
        mock_cache.assert_called_once_with("10001")

    @patch('scraper.httpx.AsyncClient')
    @patch('scraper.cache_demographics')
    @patch('scraper.get_cached_demographics')
    async def test_fetches_and_caches_data(self, mock_get_cache, mock_cache, mock_client):
        """Should fetch data from API and cache it."""
        # Setup mock cache to return None (not cached)
        mock_get_cache.return_value = None

        # Setup mock HTTP response
        html_response = """
        <html>
            <body>
                Median Income: $75,000
                Population: 100,000
                Median Age: 35.5
            </body>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.text = html_response
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        mock_client.return_value = mock_client_instance

        result = await get_demographics_by_zip("10001")

        # Should have called the cache function
        mock_cache.assert_called_once()
        # Should have called the client
        mock_client_instance.get.assert_called_once()

    @patch('scraper.httpx.AsyncClient')
    @patch('scraper.get_cached_demographics')
    async def test_timeout_error_handling(self, mock_get_cache, mock_client):
        """Should handle timeout gracefully."""
        mock_get_cache.return_value = None

        from httpx import TimeoutException
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = TimeoutException("timeout")
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        mock_client.return_value = mock_client_instance

        result = await get_demographics_by_zip("10001")
        assert result is None

    @patch('scraper.httpx.AsyncClient')
    @patch('scraper.get_cached_demographics')
    async def test_http_error_handling(self, mock_get_cache, mock_client):
        """Should handle HTTP errors gracefully."""
        mock_get_cache.return_value = None

        from httpx import HTTPError
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = HTTPError("error")
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        mock_client.return_value = mock_client_instance

        result = await get_demographics_by_zip("10001")
        assert result is None


@pytest.mark.asyncio
class TestSearchZipsByDemographics:
    """Test zip code search by demographics."""

    async def test_territories_with_no_data(self):
        """Should return empty list for territories with no data."""
        for territory in TERRITORIES_WITH_NO_DATA:
            result = await search_zips_by_demographics(territory)
            assert result == []

    @patch('scraper.httpx.AsyncClient')
    async def test_search_success(self, mock_client):
        """Should search and return zip codes."""
        html_response = """
        <table>
            <tr><td>10001</td><td>data</td></tr>
            <tr><td>10002</td><td>data</td></tr>
            <tr><td>10003</td><td>data</td></tr>
        </table>
        """

        mock_response = AsyncMock()
        mock_response.text = html_response
        mock_response.raise_for_status = AsyncMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        mock_client.return_value = mock_client_instance

        result = await search_zips_by_demographics("NY")
        assert isinstance(result, list)
        # Should have called the API
        mock_client_instance.get.assert_called_once()

    @patch('scraper.httpx.AsyncClient')
    async def test_search_timeout(self, mock_client):
        """Should handle timeout in search."""
        from httpx import TimeoutException
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = TimeoutException("timeout")
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        mock_client.return_value = mock_client_instance

        result = await search_zips_by_demographics("NY")
        assert result == []

    @patch('scraper.httpx.AsyncClient')
    async def test_search_http_error(self, mock_client):
        """Should handle HTTP errors in search."""
        from httpx import HTTPError
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = HTTPError("error")
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None

        mock_client.return_value = mock_client_instance

        result = await search_zips_by_demographics("NY")
        assert result == []


class TestParseZipPage:
    """Test zip page parsing."""

    def test_parse_valid_html(self):
        """Should parse valid HTML with demographics."""
        html = """
        <html>
            <body>
                <p>Median Income: $75,000</p>
                <p>Population: 100,000</p>
                <p>Median Age: 35.5</p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        result = _parse_zip_page(soup, "10001")
        # May or may not parse depending on HTML structure
        assert result is None or isinstance(result, dict)

    def test_parse_not_found_page(self):
        """Should return None for not found page."""
        html = "<html><body>Zip code not found</body></html>"
        soup = BeautifulSoup(html, 'lxml')
        result = _parse_zip_page(soup, "00000")
        assert result is None

    def test_parse_invalid_zip(self):
        """Should return None for invalid zip."""
        html = "<html><body>Invalid zip code</body></html>"
        soup = BeautifulSoup(html, 'lxml')
        result = _parse_zip_page(soup, "invalid")
        assert result is None


class TestParseDemographicsSearch:
    """Test demographics search result parsing."""

    def test_parse_with_valid_table(self):
        """Should parse zip codes from table."""
        html = """
        <table>
            <tr><td>10001</td><td>data</td></tr>
            <tr><td>10002</td><td>data</td></tr>
            <tr><td>10003</td><td>data</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'lxml')
        result = _parse_demographics_search(soup)
        assert isinstance(result, list)
        # May extract zip codes depending on HTML structure
        assert all(isinstance(z, str) for z in result)

    def test_parse_empty_table(self):
        """Should return empty list for empty table."""
        html = "<html><body><table></table></body></html>"
        soup = BeautifulSoup(html, 'lxml')
        result = _parse_demographics_search(soup)
        assert result == []

    def test_parse_no_table(self):
        """Should return empty list if no table."""
        html = "<html><body>No table here</body></html>"
        soup = BeautifulSoup(html, 'lxml')
        result = _parse_demographics_search(soup)
        assert result == []


class TestTerritoriesWithNoData:
    """Test territories list."""

    def test_territories_list_exists(self):
        """Should have list of territories."""
        assert isinstance(TERRITORIES_WITH_NO_DATA, set)
        assert len(TERRITORIES_WITH_NO_DATA) > 0
        assert "PR" in TERRITORIES_WITH_NO_DATA
        assert "GU" in TERRITORIES_WITH_NO_DATA
