import logging
import httpx
from pytrends.request import TrendReq
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


async def fetch_fng_data() -> dict | None:
    """Fetch the raw Fear & Greed data from CNN."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
def fetch_google_trends_sentiment(keywords: List[str] = None, period_days: int = 7) -> Dict[str, any]:
    """
    Fetch relative search interest for market sentiment-related keywords on Google Trends.
    Returns interest levels.
    """
    if keywords is None:
        keywords = [
            "stock market crash",
            "recession",
            "inflation",
            "bull market",
            "buy stocks",
            "market rally"
        ]

    pytrends = TrendReq(hl='en-US', tz=360)
    pytrends.build_payload(keywords, timeframe='now 7-d', geo='')

    data = pytrends.interest_over_time()
    if data.empty:
        return {"error": "No data returned"}

    # Weekly average interest for each keyword
    average_interest = data[keywords].mean().to_dict()

    return {
        "interest_scores": average_interest,
    }