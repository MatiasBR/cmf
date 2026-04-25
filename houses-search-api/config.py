from dotenv import load_dotenv
import os

load_dotenv()

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_TITLE = os.getenv("API_TITLE", "Houses Search API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")

# Database
DATABASE_FILE = os.getenv("DATABASE_FILE", "houses.db")

# CSV Data Source
CSV_URL = os.getenv("CSV_URL", "https://getgloby-realtor-challenge.s3.us-east-1.amazonaws.com/realtor-data.csv")

# Demographics API
DEMOGRAPHICS_API_TIMEOUT = int(os.getenv("DEMOGRAPHICS_API_TIMEOUT", "10"))
DEMOGRAPHICS_CACHE_TTL_HOURS = int(os.getenv("DEMOGRAPHICS_CACHE_TTL_HOURS", "24"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
