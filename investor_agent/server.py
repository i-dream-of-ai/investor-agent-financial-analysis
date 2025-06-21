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


@mcp.tool()
def get_ticker_data(ticker: str) -> dict:
    """Get comprehensive ticker data: info, news, metrics, recommendations, upgrades, calendar."""
    info = yfinance_utils.get_ticker_info(ticker)
    if not info:
        raise ValueError(f"No information available for {ticker}")

    data = {"info": info}

    if calendar := yfinance_utils.get_calendar(ticker):
        data["calendar"] = calendar

    if (recommendations := yfinance_utils.get_recommendations(ticker)) is not None and not recommendations.empty:
        data["recommendations"] = recommendations.to_dict('records')

    if (upgrades := yfinance_utils.get_upgrades_downgrades(ticker)) is not None and not upgrades.empty:
        data["upgrades_downgrades"] = upgrades.to_dict('records')

    if news := yfinance_utils.get_news(ticker):
        data["news"] = news

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

    return df.head(num_options).to_dict('records')


@mcp.tool()
def get_price_history(
    ticker: str,
    period: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] = "1mo"
) -> dict:
    """Get historical price data."""
    history = yfinance_utils.get_price_history(ticker, period)
    if history is None or history.empty:
        raise ValueError(f"No historical data found for {ticker}")

    return history.to_dict('records')

@mcp.tool()
def get_financial_statements(
    ticker: str,
    statement_type: Literal["income", "balance", "cash"] = "income",
    frequency: Literal["quarterly", "annual"] = "quarterly",
) -> dict:
    """Get financial statements."""
    data = yfinance_utils.get_financial_statements(ticker, statement_type, frequency)

    if data is None or data.empty:
        raise ValueError(f"No {statement_type} statement data found for {ticker}")

    return data.to_dict('records')

@mcp.tool()
def get_institutional_holders(ticker: str, top_n: int = 20) -> dict:
    """Get major institutional and mutual fund holders."""
    inst_holders, fund_holders = yfinance_utils.get_institutional_holders(ticker, top_n)

    if (inst_holders is None or inst_holders.empty) and (fund_holders is None or fund_holders.empty):
        raise ValueError(f"No institutional holder data found for {ticker}")

    result = {}

    if inst_holders is not None and not inst_holders.empty:
        result["institutional_holders"] = inst_holders.to_dict('records')

    if fund_holders is not None and not fund_holders.empty:
        result["mutual_fund_holders"] = fund_holders.to_dict('records')

    return result

@mcp.tool()
def get_earnings_history(ticker: str) -> dict:
    """Get earnings history with estimates and surprises."""
    earnings_history = yfinance_utils.get_earnings_history(ticker)

    if earnings_history is None or earnings_history.empty:
        raise ValueError(f"No earnings history data found for {ticker}")

    return earnings_history.to_dict('records')

@mcp.tool()
def get_insider_trades(ticker: str) -> dict:
    """Get recent insider trading activity."""
    trades = yfinance_utils.get_insider_trades(ticker)

    if trades is None or trades.empty:
        raise ValueError(f"No insider trading data found for {ticker}")

    return trades.to_dict('records')

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
        history = yfinance_utils.get_price_history(ticker, period=period)
        if history is None or history.empty:
            raise ValueError(f"No historical data found for {ticker} for period {period}")
        if 'Close' not in history.columns:
             raise ValueError(f"Historical data for {ticker} is missing the 'Close' price")

        close_prices = history['Close'].values

        # More accurate minimum data requirements
        min_required = {
            "SMA": timeperiod, "EMA": timeperiod * 2, "RSI": timeperiod + 1,
            "MACD": slowperiod + signalperiod, "BBANDS": timeperiod
        }.get(indicator, timeperiod)

        if len(close_prices) < min_required:
            raise ValueError(f"Insufficient data for {indicator} ({len(close_prices)} points, need {min_required})")

        # Calculate indicators
        import numpy as np
        if indicator == "SMA":
            result = {"sma": talib.SMA(close_prices, timeperiod=timeperiod)}
        elif indicator == "EMA":
            result = {"ema": talib.EMA(close_prices, timeperiod=timeperiod)}
        elif indicator == "RSI":
            result = {"rsi": talib.RSI(close_prices, timeperiod=timeperiod)}
        elif indicator == "MACD":
            macd, signal, histogram = talib.MACD(close_prices, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
            result = {"macd": macd, "signal": signal, "histogram": histogram}
        elif indicator == "BBANDS":
            upper, middle, lower = talib.BBANDS(close_prices, timeperiod=timeperiod, nbdevup=nbdev, nbdevdn=nbdev, matype=matype)
            result = {"upper_band": upper, "middle_band": middle, "lower_band": lower}

        # Convert to lists, handle NaN, and limit results
        dates = history.index.strftime('%Y-%m-%d').tolist()
        if num_results > 0 and len(dates) > num_results:
            start_idx = len(dates) - num_results
            dates = dates[start_idx:]
            history = history.iloc[start_idx:]

        # Create aligned data with proper NaN handling
        data = []
        for i, date in enumerate(dates):
            point = {"date": date, "price": history.iloc[i].to_dict()}
            point["indicators"] = {}
            for key, values in result.items():
                val = values[start_idx + i] if num_results > 0 and len(dates) < len(values) else values[i]
                point["indicators"][key] = None if np.isnan(val) else float(val)
            data.append(point)

        return data

@mcp.prompt()
def investment_principles() -> str:
    """Core investment principles and guidelines."""
    return """
Core investment principles:
• Play for meaningful stakes
• Resist the allure of diversification. Invest in ventures that are genuinely interesting
• When the ship starts to sink, jump
• Never hesitate to abandon a venture if something more attractive comes into view
• Nobody knows the future
• Prices move based on human emotions, not quantifiable measures
• History does not necessarily repeat itself. Ignore chart patterns
• Disregard what everybody says until you've thought through yourself
• Don't average down a bad trade
• React to events as they unfold in the present instead of planning for unknowable futures
• Reevaluate every investment quarterly: Would you buy this today if presented for the first time?
"""

@mcp.prompt()
async def portfolio_construction_prompt() -> str:
    """Portfolio construction strategy using tail-hedging via married puts."""
    return """
Portfolio construction with tail-hedge strategy:

1. Analyze current portfolio: asset classes, correlation, historical performance, volatility, drawdown risk
2. Design core portfolio: maintain market exposure, align with risk tolerance, use low-cost index funds/ETFs
3. Develop tail-hedge (~3% allocation): married put strategy with 3-month puts, strike 15% below current price
4. Specify rebalancing: when to reset hedges, how to redeploy gains, account for time decay
5. Include performance metrics: expected returns in various scenarios, impact on long-term CAGR, volatility reduction
6. Implementation: specific securities, timing, tax implications

Use available tools for analysis. Focus on reducing "volatility tax" while maintaining growth potential.
"""

@mcp.tool()
async def get_cnn_fear_greed_index(days: int = 30) -> dict:
    """Get CNN Fear & Greed Index with current value and optional historical data.

    Args:
        days: Number of historical days to include (0 = current only, >0 = current + history)
    """
    logger.info(f"Fetching comprehensive CNN Fear & Greed Index for {days} days")

    if days < 0:
        raise ValueError("Days must be zero or a positive integer")

    data = await fetch_fng_data()

    if not data:
        raise RuntimeError("Unable to fetch CNN Fear & Greed Index data")

    # Get current data
    fear_and_greed = data.get("fear_and_greed", {})
    current_score = int(fear_and_greed.get("score", 0))
    current_rating = fear_and_greed.get("rating", "Unknown")
    current_timestamp = fear_and_greed.get("timestamp")

    result = {
        "current": {
            "score": current_score,
            "rating": current_rating
        }
    }

    # Add current timestamp if available
    if current_timestamp:
        result["current"]["timestamp"] = current_timestamp

    # Get historical data (only if days > 0)
    history = data.get("fear_and_greed_historical", [])
    if history and days > 0:
        # Limit to the requested number of days
        limited_history = history[:min(days, len(history))]
        result["historical"] = limited_history

    return result


@mcp.tool()
async def get_crypto_fear_greed_index_history(days: int = 30) -> dict:
    """Get historical Crypto Fear & Greed Index data."""
    logger.info(f"Fetching crypto Fear & Greed Index for {days} days")

    return await fetch_crypto_fear_greed_history(days)