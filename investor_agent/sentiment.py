import logging
import httpx

logger = logging.getLogger(__name__)


async def fetch_fng_data() -> dict | None:
    """Fetch the raw Fear & Greed data from CNN."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
    }

    # Use caching transport to avoid refetching identical data too frequently
    transport = None
    try:
        from httpx_caching import CachingTransport  # type: ignore
        transport = CachingTransport()
    except Exception:
        transport = None

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers=headers
        )
        response.raise_for_status()
        return response.json()