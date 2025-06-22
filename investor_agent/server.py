import logging
from typing import Literal
import sys

from mcp.server.fastmcp import FastMCP
try:
    import talib  # type: ignore
    _ta_available = True
except ImportError:
    _ta_available = False

from . import yfinance_utils
from .sentiment import fetch_fng_data
from .crypto import fetch_crypto_fear_greed_history

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

mcp = FastMCP("Investor-Agent", dependencies=["yfinance", "httpx", "pandas"]) # TA-Lib is optional

FearGreedIndicator = Literal[
    "fear_and_greed",
    "fear_and_greed_historical",
    "put_call_options",
    "market_volatility_vix",
    "market_volatility_vix_50",
    "junk_bond_demand",
    "safe_haven_demand"
]

@mcp.tool()
async def get_cnn_fear_greed_index(
    days: int = 0,
    indicators: list[FearGreedIndicator] | None = None
) -> dict:
    """Max 30 days of historical data."""
    data = await fetch_fng_data()
    if not data:
        raise RuntimeError("Unable to fetch CNN Fear & Greed Index data")

    if indicators:
        invalid_keys = set(indicators) - set(data.keys())
        if invalid_keys:
            raise ValueError(f"Invalid indicators: {list(invalid_keys)}. Available: {list(data.keys())}")
        data = {k: v for k, v in data.items() if k in indicators}

    # Exclude fear_and_greed_historical when days = 0
    if days == 0:
        data = {k: v for k, v in data.items() if k != "fear_and_greed_historical"}

    # Handle historical data based on days parameter
    max_days = min(days, 30) if days > 0 else 0
    for key, value in data.items():
        if isinstance(value, dict) and "data" in value:
            if days == 0:
                data[key] = {k: v for k, v in value.items() if k != "data"}
            elif len(value["data"]) > max_days:
                data[key] = {**value, "data": value["data"][:max_days]}

    return data

@mcp.tool()
async def get_crypto_fear_greed_index(days: int = 7) -> dict:
    """Get historical Crypto Fear & Greed Index data."""
    logger.info(f"Fetching crypto Fear & Greed Index for {days} days")

    return await fetch_crypto_fear_greed_history(days)

@mcp.tool()
def get_ticker_data(
    ticker: str,
    max_news: int = 5,
    max_recommendations: int = 5,
    max_upgrades: int = 5
) -> dict:
    """
    Returns:
    - info: Core financial metrics (P/E ratios, margins, growth rates, debt ratios, market cap, EPS, etc.)
    - calendar: Upcoming earnings dates and dividend dates
    - news: Recent news articles (headlines, dates, sources)
    - recommendations: Latest analyst recommendations (buy/sell/hold ratings)
    - upgrades_downgrades: Recent analyst rating changes
    """
    info = yfinance_utils.get_ticker_info(ticker)
    if not info:
        raise ValueError(f"No information available for {ticker}")

    # Filter out clearly irrelevant metadata and technical details
    excluded_fields = {
        # Exchange/trading metadata
        'exchange', 'quoteType', 'exchangeTimezoneName', 'exchangeTimezoneShortName',
        'fullExchangeName', 'gmtOffSetMilliseconds', 'sourceInterval', 'exchangeDataDelayedBy',
        'tradeable', 'triggerable', 'market', 'marketState', 'financialCurrency',
        'quoteSourceName', 'messageBoardId', 'priceHint',

        # Micro-trading data (more relevant for day traders)
        'bid', 'ask', 'bidSize', 'askSize', 'preMarketChange', 'preMarketChangePercent',
        'preMarketPrice', 'preMarketTime', 'postMarketChange', 'postMarketChangePercent',
        'postMarketPrice', 'postMarketTime', 'regularMarketOpen', 'regularMarketTime',
        'regularMarketPreviousClose', 'regularMarketDayRange', 'regularMarketDayLow', 'regularMarketDayHigh',

        # Administrative/contact details
        'address1', 'address2', 'city', 'state', 'zip', 'phone', 'fax', 'website',
        'irWebsite', 'maxAge', 'uuid',

        # Complex timestamp fields (keep simple date fields)
        'earningsTimestamp', 'earningsTimestampStart', 'earningsTimestampEnd',
        'mostRecentQuarter', 'nextFiscalYearEnd', 'lastFiscalYearEnd',
        'sharesShortPreviousMonthDate', 'dateShortInterest',

        # Redundant price/change calculations
        'regularMarketChange', 'regularMarketChangePercent', 'fiftyTwoWeekLowChange',
        'fiftyTwoWeekLowChangePercent', 'fiftyTwoWeekHighChange', 'fiftyTwoWeekHighChangePercent',
        'fiftyDayAverageChange', 'fiftyDayAverageChangePercent', 'twoHundredDayAverageChange',
        'twoHundredDayAverageChangePercent',

        # Governance/risk scores (specialized use case)
        'compensationAsOfEpochDate', 'compensationRisk', 'auditRisk', 'boardRisk',
        'shareHolderRightsRisk', 'overallRisk', 'governanceEpochDate',

        # ESG data (valuable but specialized)
        'esgPopulated', 'environmentScore', 'socialScore', 'governanceScore',

        # Redundant averages (keep the most useful ones)
        'averageDailyVolume10Day', 'averageVolume10days',  # keep averageVolume and averageDailyVolume3Month

        # Split/dividend detail fields (keep the rates/yields)
        'lastSplitFactor', 'lastSplitDate', 'lastDividendValue', 'lastDividendDate',

        # Display/formatting fields
        'displayName', 'shortName',  # keep longName for full company name
    }

    filtered_info = {k: v for k, v in info.items() if k not in excluded_fields}
    logger.info(f"Filtered ticker info from {len(info)} to {len(filtered_info)} fields by excluding {len(excluded_fields)} irrelevant fields")
    data = {"info": filtered_info}

    if calendar := yfinance_utils.get_calendar(ticker):
        data["calendar"] = calendar

    if news := yfinance_utils.get_news(ticker, limit=max_news):
        data["news"] = news

    recommendations = yfinance_utils.get_recommendations(ticker, limit=max_recommendations)
    if recommendations is not None and not recommendations.empty:
        data["recommendations"] = recommendations.to_dict('split')

    upgrades = yfinance_utils.get_upgrades_downgrades(ticker, limit=max_upgrades)
    if upgrades is not None and not upgrades.empty:
        data["upgrades_downgrades"] = upgrades.to_dict('split')

    return data

@mcp.tool()
def get_options(
    ticker_symbol: str,
    num_options: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    strike_lower: float | None = None,
    strike_upper: float | None = None,
    option_type: Literal["C", "P"] | None = None,
) -> dict:
    """Get options data. Dates: YYYY-MM-DD. Type: C=calls, P=puts."""
    df, error = yfinance_utils.get_filtered_options(
        ticker_symbol, start_date, end_date, strike_lower, strike_upper, option_type
    )
    if error:
        raise ValueError(error)

    return df.head(num_options).to_dict('split')


@mcp.tool()
def get_price_history(
    ticker: str,
    period: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] = "1mo"
) -> dict:
    """Get historical OHLCV data: daily intervals for ≤1y periods, monthly intervals for ≥2y periods."""
    # Use monthly intervals for longer periods to reduce data volume
    if period in ["2y", "5y", "10y", "max"]:
        interval = "1mo"
        logger.info(f"Using monthly interval for {period} period to optimize data volume")
    else:
        interval = "1d"
        logger.info(f"Using daily interval for {period} period")

    history = yfinance_utils.get_price_history(ticker, period, interval)
    if history is None or history.empty:
        raise ValueError(f"No historical data found for {ticker}")

    return history.to_dict('split')

@mcp.tool()
def get_financial_statements(
    ticker: str,
    statement_type: Literal["income", "balance", "cash"] = "income",
    frequency: Literal["quarterly", "annual"] = "quarterly",
    max_periods: int = 8
) -> dict:
    data = yfinance_utils.get_financial_statements(ticker, statement_type, frequency)

    if data is None or data.empty:
        raise ValueError(f"No {statement_type} statement data found for {ticker}")

    # Limit to most recent periods if data is extensive
    if len(data.columns) > max_periods:
        # Keep the most recent periods (columns are typically in reverse chronological order)
        data = data.iloc[:, :max_periods]
        logger.info(f"Limited {statement_type} statement to {max_periods} most recent periods to optimize context size")

    return data.to_dict('split')

@mcp.tool()
def get_institutional_holders(ticker: str, top_n: int = 20) -> dict:
    """Get major institutional and mutual fund holders."""
    inst_holders, fund_holders = yfinance_utils.get_institutional_holders(ticker, top_n)

    if (inst_holders is None or inst_holders.empty) and (fund_holders is None or fund_holders.empty):
        raise ValueError(f"No institutional holder data found for {ticker}")

    return {
        key: data.to_dict('split')
        for key, data in [
            ("institutional_holders", inst_holders),
            ("mutual_fund_holders", fund_holders)
        ]
        if data is not None and not data.empty
    }

@mcp.tool()
def get_earnings_history(ticker: str, max_entries: int = 8) -> dict:
    earnings_history = yfinance_utils.get_earnings_history(ticker, limit=max_entries)

    if earnings_history is None or earnings_history.empty:
        raise ValueError(f"No earnings history data found for {ticker}")

    return earnings_history.to_dict('split')

@mcp.tool()
def get_insider_trades(ticker: str, max_trades: int = 20) -> dict:
    trades = yfinance_utils.get_insider_trades(ticker, limit=max_trades)

    if trades is None or trades.empty:
        raise ValueError(f"No insider trading data found for {ticker}")

    return trades.to_dict('split')

# Only register the technical indicator tool if TA-Lib is available
if _ta_available:
    @mcp.tool()
    def calculate_technical_indicator(
        ticker: str,
        indicator: Literal["SMA", "EMA", "RSI", "MACD", "BBANDS"],
        period: Literal["1mo", "3mo", "6mo", "1y", "2y", "5y"] = "1y",
        timeperiod: int = 14,  # Default timeperiod for SMA, EMA, RSI
        fastperiod: int = 12,  # Default for MACD fast EMA
        slowperiod: int = 26,  # Default for MACD slow EMA
        signalperiod: int = 9,   # Default for MACD signal line
        nbdev: int = 2,        # Default standard deviation for BBANDS
        matype: int = 0,       # Default MA type for BBANDS (0=SMA)
        num_results: int = 50  # Number of recent results to return
    ) -> dict:
        """Calculate technical indicators with proper date alignment and result limiting."""
        import numpy as np

        history = yfinance_utils.get_price_history(ticker, period=period, interval="1d")
        if history is None or history.empty or 'Close' not in history.columns:
            raise ValueError(f"No valid historical data found for {ticker}")

        close_prices = history['Close'].values
        min_required = {
            "SMA": timeperiod, "EMA": timeperiod * 2, "RSI": timeperiod + 1,
            "MACD": slowperiod + signalperiod, "BBANDS": timeperiod
        }.get(indicator, timeperiod)

        if len(close_prices) < min_required:
            raise ValueError(f"Insufficient data for {indicator} ({len(close_prices)} points, need {min_required})")

        # Calculate indicators using mapping
        indicator_funcs = {
            "SMA": lambda: {"sma": talib.SMA(close_prices, timeperiod=timeperiod)},
            "EMA": lambda: {"ema": talib.EMA(close_prices, timeperiod=timeperiod)},
            "RSI": lambda: {"rsi": talib.RSI(close_prices, timeperiod=timeperiod)},
            "MACD": lambda: dict(zip(["macd", "signal", "histogram"],
                                   talib.MACD(close_prices, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod))),
            "BBANDS": lambda: dict(zip(["upper_band", "middle_band", "lower_band"],
                                     talib.BBANDS(close_prices, timeperiod=timeperiod, nbdevup=nbdev, nbdevdn=nbdev, matype=matype)))
        }
        result = indicator_funcs[indicator]()

        # Limit results and prepare data
        dates = history.index.strftime('%Y-%m-%d').tolist()
        start_idx = max(0, len(dates) - num_results) if num_results > 0 else 0

        return [
            {
                "date": dates[i],
                "price": history.iloc[i].to_dict(),
                "indicators": {
                    key: None if np.isnan(val := values[i]) else float(val)
                    for key, values in result.items()
                }
            }
            for i in range(start_idx, len(dates))
        ]