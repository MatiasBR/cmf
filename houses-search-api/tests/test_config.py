import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    API_HOST, API_PORT, API_TITLE, API_VERSION,
    DATABASE_FILE, CSV_URL, DEMOGRAPHICS_API_TIMEOUT,
    DEMOGRAPHICS_CACHE_TTL_HOURS, LOG_LEVEL, CORS_ORIGINS
)


class TestConfig:
    """Test configuration loading."""

    def test_api_config_exists(self):
        """API configuration should be loaded."""
        assert API_HOST is not None
        assert API_PORT is not None
        assert isinstance(API_PORT, int)
        assert API_PORT > 0

    def test_database_config_exists(self):
        """Database configuration should be loaded."""
        assert DATABASE_FILE is not None
        assert isinstance(DATABASE_FILE, str)

    def test_csv_url_exists(self):
        """CSV URL should be configured."""
        assert CSV_URL is not None
        assert isinstance(CSV_URL, str)
        assert CSV_URL.startswith("http")

    def test_timeout_is_integer(self):
        """Timeout should be integer."""
        assert isinstance(DEMOGRAPHICS_API_TIMEOUT, int)
        assert DEMOGRAPHICS_API_TIMEOUT > 0

    def test_cache_ttl_is_integer(self):
        """Cache TTL should be integer."""
        assert isinstance(DEMOGRAPHICS_CACHE_TTL_HOURS, int)
        assert DEMOGRAPHICS_CACHE_TTL_HOURS > 0

    def test_log_level_is_valid(self):
        """Log level should be valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert LOG_LEVEL in valid_levels

    def test_cors_origins_is_list(self):
        """CORS origins should be a list."""
        assert isinstance(CORS_ORIGINS, list)
