import httpx
import logging
from bs4 import BeautifulSoup
from config import DEMOGRAPHICS_API_TIMEOUT
from database import get_cached_demographics, cache_demographics

logger = logging.getLogger(__name__)

TERRITORIES_WITH_NO_DATA = {"AS", "GU", "MP", "PR", "VI"}


async def get_demographics_by_zip(zip_code: str) -> dict | None:
    """
    Fetch demographics data for a zip code from ZipWho.
    Caches results with 24-hour TTL.
    Returns dict with zip_code, median_income, population, median_age, or None if not found.
    """
    cached = await get_cached_demographics(zip_code)
    if cached is not None:
        logger.info(f"Using cached demographics for zip {zip_code}")
        return cached

    try:
        url = f"https://zipwho.com/?mode=zip&zip={zip_code}"
        async with httpx.AsyncClient(timeout=float(DEMOGRAPHICS_API_TIMEOUT)) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        demographics = _parse_zip_page(soup, zip_code)

        if demographics:
            await cache_demographics(zip_code, demographics)
            logger.info(f"Fetched and cached demographics for zip {zip_code}")
            return demographics
        else:
            logger.warning(f"Could not parse demographics for zip {zip_code}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching demographics for zip {zip_code}")
        return None
    except httpx.HTTPError as e:
        logger.warning(f"HTTP error fetching demographics for zip {zip_code}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching demographics for zip {zip_code}: {e}")
        return None


def _parse_zip_page(soup: BeautifulSoup, zip_code: str) -> dict | None:
    """Parse ZipWho page and extract demographics data."""
    try:
        # Try to find the main info section
        # ZipWho typically displays data in table cells or divs
        median_income = None
        population = None
        median_age = None

        # Look for patterns in the page
        text = soup.get_text()

        # Check if zip code was found
        if "not found" in text.lower() or "invalid" in text.lower():
            return None

        # Try to extract data from common patterns
        # This is a basic implementation - ZipWho's HTML structure varies
        # Look for patterns like "Median Income: $X" or similar
        for line in text.split('\n'):
            line_lower = line.lower().strip()

            if 'median income' in line_lower:
                # Extract dollar amount
                import re
                matches = re.findall(r'\$[\d,]+', line)
                if matches:
                    median_income = int(matches[0].replace('$', '').replace(',', ''))

            elif 'population' in line_lower:
                import re
                matches = re.findall(r'\d+(?:,\d+)*(?!\w)', line)
                if matches:
                    population = int(matches[0].replace(',', ''))

            elif 'median age' in line_lower or 'age' in line_lower:
                import re
                matches = re.findall(r'\d+\.?\d*', line)
                if matches:
                    median_age = float(matches[0])

        if median_income or population or median_age:
            return {
                "zip_code": zip_code,
                "median_income": median_income,
                "population": population,
                "median_age": median_age
            }

        return None

    except Exception as e:
        logger.error(f"Error parsing demographics page: {e}")
        return None


async def search_zips_by_demographics(
    state_code: str,
    min_population: int = 0,
    max_population: int = 999999,
    min_median_income: int = 0,
    max_median_income: int = 999999,
    min_median_age: float = 0,
    max_median_age: float = 999
) -> list[str]:
    """
    Search for zip codes matching demographic criteria in a given state.
    Returns list of zip code strings, or empty list on error.
    Immediately returns empty list for territories with no data.
    """
    if state_code in TERRITORIES_WITH_NO_DATA:
        logger.info(f"State {state_code} has no data in ZipWho, returning empty list")
        return []

    try:
        url = (
            f"https://zipwho.com/?mode=demo&"
            f"filters=MedianIncome-{min_median_income}-{max_median_income}_"
            f"Population-{min_population}-{max_population}_"
            f"MedianAge-{min_median_age}-{max_median_age}&"
            f"state={state_code}"
        )

        async with httpx.AsyncClient(timeout=float(DEMOGRAPHICS_API_TIMEOUT)) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        zip_codes = _parse_demographics_search(soup)

        logger.info(f"Found {len(zip_codes)} zip codes for {state_code} with demographic filters")
        return zip_codes

    except httpx.TimeoutException:
        logger.warning(f"Timeout searching demographics for {state_code}")
        return []
    except httpx.HTTPError as e:
        logger.warning(f"HTTP error searching demographics for {state_code}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error searching demographics for {state_code}: {e}")
        return []


def _parse_demographics_search(soup: BeautifulSoup) -> list[str]:
    """Parse ZipWho demographics search results and extract zip codes."""
    try:
        zip_codes = []

        # Look for table rows containing zip codes
        # ZipWho typically shows results in a table
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if cells:
                    # First cell often contains the zip code
                    first_cell_text = cells[0].get_text(strip=True)
                    if first_cell_text.isdigit() and len(first_cell_text) == 5:
                        zip_codes.append(first_cell_text)

        return zip_codes

    except Exception as e:
        logger.error(f"Error parsing demographics search results: {e}")
        return []
