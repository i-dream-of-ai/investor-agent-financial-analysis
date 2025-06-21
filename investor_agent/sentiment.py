import logging
from datetime import datetime, timezone
import httpx

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
        data = response.json()

        def parse_timestamp(ts_value):
            if isinstance(ts_value, (int, float)):
                return int(ts_value)
            if isinstance(ts_value, str):
                try:
                    # Fix timezone offset format if needed
                    if ts_value[-3:-2] == ":":
                        ts_value = ts_value[:-3] + ts_value[-2:]
                    dt_obj = datetime.fromisoformat(ts_value).astimezone(timezone.utc)
                    return int(dt_obj.timestamp() * 1000)
                except ValueError:
                    logger.warning(f"Could not parse timestamp: {ts_value}")
            return None

        # Process current timestamp
        if (fg := data.get('fear_and_greed', {})) and 'timestamp' in fg:
            if parsed_ts := parse_timestamp(fg['timestamp']):
                fg['timestamp'] = parsed_ts
            else:
                del fg['timestamp']

        # Process historical data
        if hist_data := data.get('fear_and_greed_historical', {}):
            if isinstance(hist_data, dict) and 'data' in hist_data:
                entries = hist_data['data']
                processed = [
                    {**entry, 'timestamp': parsed_ts, 'score': entry['y']}
                    for entry in entries
                    if isinstance(entry, dict) and 'x' in entry and 'y' in entry
                    and (parsed_ts := parse_timestamp(entry['x'])) is not None
                ]
                data['fear_and_greed_historical'] = processed
            else:
                data['fear_and_greed_historical'] = []

        return data