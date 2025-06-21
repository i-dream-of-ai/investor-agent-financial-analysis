import logging
import httpx

logger = logging.getLogger(__name__)


async def fetch_crypto_fear_greed_history(days: int) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.alternative.me/fng/", params={"limit": days})
        response.raise_for_status()
        data = response.json()["data"]
    return data