from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Literal
from datetime import datetime
import time
from functools import wraps

import yfinance as yf
from yfinance.exceptions import YFRateLimitError
import pandas as pd

logger = logging.getLogger(__name__)

def retry_on_rate_limit(max_retries: int = 3, base_delay: float = 5.0, success_delay: float = 1.5):
    """Decorator to retry function calls on rate limit errors with exponential backoff.

    Based on 2025 yfinance best practices:
    - Yahoo Finance has tightened rate limits significantly
    - Recommended delays: 5s, 15s, 45s for better success rates
    - Users report that shorter delays (1-2s) are often insufficient
    - Adding delays after successful calls helps prevent rate limiting
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    # Add a small delay after successful requests to prevent rate limiting
                    if success_delay > 0:
                        time.sleep(success_delay)
                    return result
                except (YFRateLimitError, Exception) as e:
                    if isinstance(e, YFRateLimitError) or "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                        if attempt < max_retries - 1:
                            # Use longer delays based on 2025 yfinance community recommendations
                            wait_time = base_delay * (3 ** attempt)  # 5s, 15s, 45s progression
                            logger.warning(f"Rate limited on attempt {attempt + 1}, waiting {wait_time}s before retry")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Max retries ({max_retries}) reached for rate limiting")
                            raise
                    else:
                        # For non-rate-limit errors, don't retry
                        raise
            return None
        return wrapper
    return decorator

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_ticker_info(ticker: str) -> dict | None:
    try:
        return yf.Ticker(ticker).get_info()
    except Exception as e:
        logger.error(f"Error retrieving ticker info for {ticker}: {e}", exc_info=True)
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_calendar(ticker: str) -> dict | None:
    """Get calendar events including earnings and dividend dates."""
    try:
        return yf.Ticker(ticker).get_calendar()
    except Exception as e:
        logger.error(f"Error retrieving calendar for {ticker}: {e}", exc_info=True)
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_recommendations(ticker: str, limit: int = 5) -> pd.DataFrame | None:
    """Get analyst recommendations.
    Returns DataFrame with columns: Firm, To Grade, From Grade, Action
    Limited to most recent entries by default.
    """
    try:
        df = yf.Ticker(ticker).get_recommendations()
        return df.head(limit) if df is not None else None
    except Exception as e:
        logger.error(f"Error retrieving recommendations for {ticker}: {e}")
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_upgrades_downgrades(ticker: str, limit: int = 5) -> pd.DataFrame | None:
    """Get upgrades/downgrades history.
    Returns DataFrame with columns: firm, toGrade, fromGrade, action
    Limited to most recent entries by default.
    """
    try:
        df = yf.Ticker(ticker).get_upgrades_downgrades()
        return df.sort_index(ascending=False).head(limit) if df is not None else None
    except Exception as e:
        logger.error(f"Error retrieving upgrades/downgrades for {ticker}: {e}")
        return None

def get_news(ticker: str, limit: int = 10) -> list[dict] | None:
    """Return recent news in `[date,title,source,url]` dicts."""

    try:
        items = yf.Ticker(ticker).get_news()[:limit]
        if not items:
            return None

        out: list[dict] = []
        for it in items:
            c = it.get("content", {})
            raw_date = c.get("pubDate") or c.get("displayTime") or ""
            try:
                date = datetime.fromisoformat(raw_date.replace("Z", "")).strftime("%Y-%m-%d")
            except Exception:
                date = raw_date[:10] if raw_date else "N/A"

            out.append({
                "date": date,
                "title": c.get("title") or "Untitled",
                "source": c.get("provider", {}).get("displayName", "Unknown"),
                "url": c.get("canonicalUrl", {}).get("url") or c.get("clickThroughUrl", {}).get("url")
            })

        return out
    except Exception as e:
        logger.error(f"get_news({ticker}) error: {e}")
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_price_history(
    ticker: str,
    period: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] = "1mo",
    interval: Literal["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"] = "1d"
) -> pd.DataFrame | None:
    try:
        return yf.Ticker(ticker).history(period=period, interval=interval)
    except Exception as e:
        logger.error(f"Error retrieving price history for {ticker}: {e}")
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_financial_statements(
    ticker: str,
    statement_type: Literal["income", "balance", "cash"] = "income",
    frequency: Literal["quarterly", "annual"] = "quarterly"
) -> pd.DataFrame | None:
    try:
        t = yf.Ticker(ticker)
        statements = {
            "income": {"annual": t.income_stmt, "quarterly": t.quarterly_income_stmt},
            "balance": {"annual": t.balance_sheet, "quarterly": t.quarterly_balance_sheet},
            "cash": {"annual": t.cashflow, "quarterly": t.quarterly_cashflow}
        }
        return statements[statement_type][frequency]
    except Exception as e:
        logger.error(f"Error retrieving {frequency} {statement_type} statement for {ticker}: {e}")
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_institutional_holders(ticker: str, top_n: int = 20) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    try:
        t = yf.Ticker(ticker)
        inst = t.get_institutional_holders()
        fund = t.get_mutualfund_holders()
        return (inst.head(top_n) if inst is not None else None,
                fund.head(top_n) if fund is not None else None)
    except Exception as e:
        logger.error(f"Error retrieving institutional holders for {ticker}: {e}")
        return None, None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_earnings_history(ticker: str, limit: int = 12) -> pd.DataFrame | None:
    """Get raw earnings history data.
    Default limit of 12 shows 3 years of quarterly earnings.
    """
    try:
        df = yf.Ticker(ticker).get_earnings_history()
        return df.head(limit) if df is not None else None
    except Exception as e:
        logger.error(f"Error retrieving earnings history for {ticker}: {e}")
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_insider_trades(ticker: str, limit: int = 30) -> pd.DataFrame | None:
    try:
        df = yf.Ticker(ticker).get_insider_transactions()
        return df.head(limit) if df is not None else None
    except Exception as e:
        logger.error(f"Error retrieving insider trades for {ticker}: {e}")
        return None

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_options_chain(
    ticker: str,
    expiry: str | None = None,
    option_type: Literal["C", "P"] | None = None
) -> tuple[pd.DataFrame | None, str | None]:
    """
    Helper function to get raw options chain data for a specific expiry.
    Args:
        ticker: Stock ticker symbol
        expiry: Expiration date
        option_type: "C" for calls, "P" for puts, None for both
    """
    try:
        if not expiry:
            return None, "No expiry date provided"

        chain = yf.Ticker(ticker).option_chain(expiry)

        if option_type == "C":
            return chain.calls, None
        elif option_type == "P":
            return chain.puts, None
        return pd.concat([chain.calls, chain.puts]), None

    except Exception as e:
        logger.error(f"Error retrieving options chain for {ticker}: {e}")
        return None, str(e)

@retry_on_rate_limit(max_retries=3, base_delay=5.0, success_delay=1.5)
def get_filtered_options(
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
    strike_lower: float | None = None,
    strike_upper: float | None = None,
    option_type: Literal["C", "P"] | None = None,
) -> tuple[pd.DataFrame | None, str | None]:
    """Get filtered options data efficiently."""
    try:
        # Validate date formats before processing
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return None, f"Invalid start_date format. Use YYYY-MM-DD"

        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return None, f"Invalid end_date format. Use YYYY-MM-DD"

        t = yf.Ticker(ticker)
        expirations = t.options

        if not expirations:
            return None, f"No options available for {ticker}"

        # Convert date strings to datetime objects once
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # Filter expiration dates before making API calls
        valid_expirations = []
        for exp in expirations:
            exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            if ((not start_date_obj or exp_date >= start_date_obj) and
                (not end_date_obj or exp_date <= end_date_obj)):
                valid_expirations.append(exp)

        if not valid_expirations:
            return None, f"No options found for {ticker} within specified date range"

        # Parallel fetch options using ThreadPoolExecutor
        filtered_option_chains = []
        with ThreadPoolExecutor() as executor:
            options_results = list(executor.map(
                lambda exp: get_options_chain(ticker, exp, option_type),
                valid_expirations
            ))

        for (chain, error), expiry in zip(options_results, valid_expirations):
            if error:
                logger.warning(f"Error fetching options for expiry {expiry}: {error}")
                continue
            if chain is not None:
                filtered_option_chains.append(chain.assign(expiryDate=expiry))

        if not filtered_option_chains:
            return None, f"No options found for {ticker} matching criteria"

        df = pd.concat(filtered_option_chains, ignore_index=True)

        # Apply strike price filters
        if strike_lower is not None or strike_upper is not None:
            mask = pd.Series(True, index=df.index)
            if strike_lower is not None:
                mask &= df['strike'] >= strike_lower
            if strike_upper is not None:
                mask &= df['strike'] <= strike_upper
            df = df[mask]

        return df.sort_values(['openInterest', 'volume'], ascending=[False, False]), None

    except Exception as e:
        logger.error(f"Error in get_filtered_options: {str(e)}", exc_info=True)
        return None, f"Failed to retrieve options data: {str(e)}"