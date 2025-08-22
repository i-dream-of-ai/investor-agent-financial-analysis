import logging
import httpx
import hishel

logger = logging.getLogger(__name__)


async def fetch_fng_data() -> dict | None:
    """Fetch the raw Fear & Greed data from CNN."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
    }

    # Use hishel caching to avoid refetching identical data too frequently
    hishel.install_cache()
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers=headers
        )
        response.raise_for_status()
        return response.json()