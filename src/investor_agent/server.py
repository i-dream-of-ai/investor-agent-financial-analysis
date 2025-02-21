import os
import logging
import sys
from datetime import datetime
from typing import Literal

from tabulate import tabulate
from dotenv import load_dotenv
from brave_search_python_client import (
    BraveSearch,
    NewsSearchRequest,
    WebSearchRequest,
)
import yfinance as yf
import pandas as pd
from mcp.server.fastmcp import FastMCP


logger = logging.getLogger(__name__)

# Load .env file and get Brave Search API key from environment
load_dotenv()
if not os.getenv("BRAVE_SEARCH_API_KEY"):
    msg = "BRAVE_SEARCH_API_KEY not found in environment"
    raise ValueError(msg)

# Initialize Brave Search client
brave_search_client = BraveSearch()

# Initialize MCP server
mcp = FastMCP("Investor-Agent")

@mcp.tool()
async def web_search(query: str) -> list:
    """Perform a web search and return results."""
    response = await brave_search_client.web(WebSearchRequest(q=query))
    return response.web.results if response.web else []

@mcp.tool()
async def news_search(query: str) -> list:
    """Search for news articles and return results."""
    response = await brave_search_client.news(NewsSearchRequest(q=query))
    return response.results or []

# Helper function to get analyst recommendations and upgrades/downgrades
def get_analyst_data(ticker_obj) -> tuple[list, list]:
    """
    Get analyst recommendations and upgrades/downgrades for a ticker.
    """
    # Get analyst recommendations
    recommendations = ticker_obj.recommendations
    recent_recommendations = (
        recommendations.tail(5).to_dict("records")
        if recommendations is not None and not recommendations.empty
        else []
    )

    # Get upgrades/downgrades
    upgrades = ticker_obj.upgrades_downgrades
    recent_upgrades = (
        upgrades.tail(5).to_dict("records")
        if upgrades is not None and not upgrades.empty
        else []
    )

    return recent_recommendations, recent_upgrades

# Helper function to get important dates
def get_important_dates(ticker_obj) -> list[list[str]]:
    """Get important upcoming dates for a ticker."""
    try:
        calendar = ticker_obj.calendar
        if not calendar:
            return []

        formatted_events = []
        for event_type, date in calendar.items():
            if pd.notnull(date):
                formatted_date = (
                    date.strftime("%Y-%m-%d")
                    if isinstance(date, pd.Timestamp)
                    else str(date)
                )
                formatted_events.append([event_type, formatted_date])

        return formatted_events
    except Exception as e:
        logger.warning(f"Failed to get important dates: {e}")
        return []

@mcp.tool()
async def get_ticker_info(ticker: str) -> str:
    """
    Get a comprehensive report for a given ticker symbol.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL')

    Returns:
        str: Formatted report containing sections:
            - Company Overview (name, sector, industry, market cap)
            - Key Metrics (price, P/E ratio, forward P/E, PEG ratio, dividend yield)
            - Important Dates (upcoming events)
            - Recent Analyst Recommendations (if available)
            - Recent Upgrades/Downgrades (if available)
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        if not info:
            return f"No information available for {ticker}"

        try:
            recent_recommendations, recent_upgrades = get_analyst_data(ticker_obj)
            important_dates = get_important_dates(ticker_obj)
        except Exception as e:
            logger.warning(f"Failed to get additional data for {ticker}: {e}")
            recent_recommendations, recent_upgrades = [], []
            important_dates = []

        sections = ["COMPANY OVERVIEW"]

        # Use DataFrame for company overview
        overview_data = [
            ["Company Name", info.get("longName", "N/A")],
            ["Sector", info.get("sector", "N/A")],
            ["Industry", info.get("industry", "N/A")],
            [
                "Market Cap",
                f"${info.get('marketCap', 0):,.2f}"
                if info.get("marketCap")
                else "N/A",
            ],
        ]
        overview_df = pd.DataFrame(overview_data, columns=["Field", "Value"])
        sections.append(tabulate(overview_df, headers="keys", tablefmt="grid", showindex=False))

        # Key Metrics section as DataFrame
        key_metrics_data = [
            [
                "Current Price",
                f"${info.get('currentPrice', 0):.2f}" if info.get("currentPrice") else "N/A",
            ],
            ["P/E Ratio", f"{info.get('peRatio', 'N/A')}"],
            ["Forward P/E", f"{info.get('forwardPE', 'N/A')}"],
            ["PEG Ratio", f"{info.get('pegRatio', 'N/A')}"],
            [
                "Dividend Yield",
                f"{info.get('dividendYield', 0)*100:.2f}%" if info.get("dividendYield") else "N/A",
            ],
        ]
        metrics_df = pd.DataFrame(key_metrics_data, columns=["Metric", "Value"])
        sections.extend(["\nKEY METRICS", tabulate(metrics_df, headers="keys", tablefmt="grid", showindex=False)])

        # Important Dates section using DataFrame if available
        if important_dates:
            dates_df = pd.DataFrame(important_dates, columns=["Event", "Date"])
            sections.extend(["\nIMPORTANT DATES", tabulate(dates_df, headers="keys", tablefmt="grid", showindex=False)])

        # Recent Analyst Recommendations using DataFrame if available
        if recent_recommendations:
            rec_df = pd.DataFrame(recent_recommendations)
            desired_cols = ["date", "firm", "toGrade", "fromGrade", "action"]
            rec_df = rec_df[[col for col in desired_cols if col in rec_df.columns]]
            sections.extend(
                [
                    "\nRECENT ANALYST RECOMMENDATIONS",
                    tabulate(rec_df, headers="keys", tablefmt="grid", showindex=False),
                ]
            )

        # Recent Upgrades/Downgrades using DataFrame if available
        if recent_upgrades:
            upg_df = pd.DataFrame(recent_upgrades)
            desired_cols = ["date", "firm", "toGrade", "fromGrade", "action"]
            upg_df = upg_df[[col for col in desired_cols if col in upg_df.columns]]
            sections.extend(
                [
                    "\nRECENT UPGRADES/DOWngrades".upper(),
                    tabulate(upg_df, headers="keys", tablefmt="grid", showindex=False),
                ]
            )

        return "\n".join(sections)

    except Exception as e:
        return f"Error retrieving investment report for {ticker}: {str(e)}"

@mcp.tool()
async def get_available_options(
    ticker_symbol: str,
    num_options: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    strike_lower: float | None = None,
    strike_upper: float | None = None,
    option_type: Literal["C", "P"] | None = None,
) -> str:
    """
    Get a list of stock options with highest open interest for a given ticker symbol.

    Args:
        ticker_symbol (str): Stock ticker symbol (e.g., 'AAPL')
        num_options (int, optional): Number of options to return. Defaults to 10
        start_date (str | None, optional): Start date in YYYY-MM-DD format
        end_date (str | None, optional): End date in YYYY-MM-DD format
        strike_lower (float | None, optional): Minimum strike price
        strike_upper (float | None, optional): Maximum strike price
        option_type (str | None, optional): Option type ('C' for calls, 'P' for puts, None for both)
    """
    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        if not ticker_obj.options:
            return f"No options available for {ticker_symbol}"

        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        expiry_dates = [
            date
            for date in ticker_obj.options
            if (not start or datetime.strptime(date, "%Y-%m-%d").date() >= start)
            and (not end or datetime.strptime(date, "%Y-%m-%d").date() <= end)
        ]
        if not expiry_dates:
            return f"No options found for {ticker_symbol} in specified date range"

        option_chains = [ticker_obj.option_chain(date) for date in expiry_dates]
        # Collect DataFrames based on option type
        option_dfs = []
        for chain in option_chains:
            if option_type == "C":
                option_dfs.append(chain.calls)
            elif option_type == "P":
                option_dfs.append(chain.puts)
            else:
                option_dfs.extend([chain.calls, chain.puts])
        df = pd.concat(option_dfs, ignore_index=True)
        df = df[
            (df["strike"] >= (strike_lower or -float("inf")))
            & (df["strike"] <= (strike_upper or float("inf")))
        ]

        if df.empty:
            return f"No options found for {ticker_symbol} matching criteria"

        top_options = df.nlargest(num_options, "openInterest").copy()

        # Create formatted columns via vectorized operations
        top_options["Type"] = top_options["contractSymbol"].apply(lambda x: "C" if "C" in x else "P")
        top_options["Strike"] = top_options["strike"].apply(lambda x: f"${x:.2f}")
        top_options["Expiry"] = pd.to_datetime(top_options["lastTradeDate"]).dt.strftime("%Y-%m-%d")
        top_options["OI"] = top_options["openInterest"].astype(int)
        top_options["Price"] = ((top_options["ask"] + top_options["bid"]) / 2).apply(lambda x: f"${x:.2f}")
        top_options["Vol"] = top_options["volume"].apply(lambda x: int(x) if x > 0 else "N/A")
        top_options["IV%"] = top_options["impliedVolatility"].apply(lambda x: f"{x*100:.1f}%")

        final_df = top_options[["Type", "Strike", "Expiry", "OI", "Price", "Vol", "IV%"]]

        return tabulate(final_df, headers="keys", tablefmt="grid", showindex=False)

    except ValueError as e:
        return f"Invalid date format. Please use YYYY-MM-DD format: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def get_price_history(
    ticker: str,
    period: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"] = "1mo",
) -> str:
    """
    Get historical price data for a ticker symbol.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL')
        period (str): Time period. Must be one of:
            '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        history = ticker_obj.history(period=period)

        if history.empty:
            return f"No historical data found for {ticker}"

        # Reset index to bring Date as a column
        history = history.reset_index()
        # Format columns for nicer display
        history["Date"] = history["Date"].dt.date
        for col in ["Open", "High", "Low", "Close"]:
            if col in history.columns:
                history[col] = history[col].apply(lambda x: f"${x:.2f}")
        if "Volume" in history.columns:
            history["Volume"] = history["Volume"].apply(lambda x: f"{x:,.0f}")

        return tabulate(history, headers="keys", tablefmt="grid", showindex=False)

    except Exception as e:
        return f"Error retrieving price history for {ticker}: {str(e)}"

@mcp.tool()
async def get_financial_statements(
    ticker: str,
    statement_type: Literal["income", "balance", "cash"] = "income",
    frequency: Literal["quarterly", "annual"] = "quarterly",
) -> str:
    """
    Get financial statements for a ticker symbol.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL')
        statement_type (str): 'income', 'balance', or 'cash'
        frequency (str): 'quarterly' or 'annual'
    """
    valid_types = ["income", "balance", "cash"]
    valid_freqs = ["quarterly", "annual"]

    if statement_type not in valid_types:
        return f"Invalid statement type. Must be one of: {', '.join(valid_types)}"
    if frequency not in valid_freqs:
        return f"Invalid frequency. Must be one of: {', '.join(valid_freqs)}"

    try:
        ticker_obj = yf.Ticker(ticker)
        data = {
            "income": ticker_obj.income_stmt if frequency == "annual" else ticker_obj.quarterly_income_stmt,
            "balance": ticker_obj.balance_sheet if frequency == "annual" else ticker_obj.quarterly_balance_sheet,
            "cash": ticker_obj.cashflow if frequency == "annual" else ticker_obj.quarterly_cashflow,
        }.get(statement_type)

        if data is None or data.empty:
            return f"No {statement_type} statement data found for {ticker}"

        # Format values in the DataFrame (values in millions USD)
        data_formatted = data.applymap(lambda x: f"${x/1e6:.1f}M" if pd.notnull(x) and isinstance(x, (int, float)) else x)
        df_formatted = data_formatted.reset_index().rename(columns={"index": "Metric"})

        return (
            f"{frequency.capitalize()} {statement_type} statement for {ticker}:\n"
            f"(Values in millions USD)\n\n"
            f"{tabulate(df_formatted, headers='keys', tablefmt='grid', showindex=False)}"
        )

    except Exception as e:
        return f"Error retrieving financial statements for {ticker}: {str(e)}"

@mcp.tool()
async def get_institutional_holders(ticker: str) -> str:
    """
    Get major institutional and mutual fund holders of the stock.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL')

    Returns:
        str: Two formatted tables:
            1. Institutional Holders:
                - Holder name
                - Shares held
                - Value of holding
                - Percentage held
                - Date reported
                - % Change
            2. Mutual Fund Holders:
                - Same columns as institutional holders
    """
    try:
        ticker_obj = yf.Ticker(ticker)

        # Get both institutional and mutual fund holders using get_ methods
        inst_holders = ticker_obj.get_institutional_holders()
        fund_holders = ticker_obj.get_mutualfund_holders()

        if (inst_holders is None or inst_holders.empty) and (fund_holders is None or fund_holders.empty):
            return f"No institutional holder data found for {ticker}"

        sections = []

        if inst_holders is not None and not inst_holders.empty:
            inst_df = inst_holders.copy()
            inst_df["Shares"] = inst_df["Shares"].apply(lambda x: f"{x:,.0f}")
            inst_df["Value"] = inst_df["Value"].apply(lambda x: f"${x:,.0f}")
            inst_df["pctHeld"] = inst_df["pctHeld"].apply(lambda x: f"{x*100:.2f}%")  # Convert to percentage
            inst_df["Date Reported"] = pd.to_datetime(inst_df["Date Reported"]).dt.strftime("%Y-%m-%d")
            inst_df["pctChange"] = inst_df["pctChange"].apply(lambda x: f"{x*100:+.2f}%" if pd.notnull(x) else "N/A")  # Add + sign and convert to percentage
            
            # Rename columns for better readability
            inst_df = inst_df.rename(columns={
                "Holder": "Institution",
                "pctHeld": "% Held",
                "pctChange": "% Change"
            })
            
            sections.append("INSTITUTIONAL HOLDERS")
            sections.append(tabulate(inst_df, headers="keys", tablefmt="grid", showindex=False))

        if fund_holders is not None and not fund_holders.empty:
            fund_df = fund_holders.copy()
            fund_df["Shares"] = fund_df["Shares"].apply(lambda x: f"{x:,.0f}")
            fund_df["Value"] = fund_df["Value"].apply(lambda x: f"${x:,.0f}")
            fund_df["pctHeld"] = fund_df["pctHeld"].apply(lambda x: f"{x*100:.2f}%")  # Convert to percentage
            fund_df["Date Reported"] = pd.to_datetime(fund_df["Date Reported"]).dt.strftime("%Y-%m-%d")
            fund_df["pctChange"] = fund_df["pctChange"].apply(lambda x: f"{x*100:+.2f}%" if pd.notnull(x) else "N/A")  # Add + sign and convert to percentage
            
            # Rename columns for better readability
            fund_df = fund_df.rename(columns={
                "Holder": "Fund",
                "pctHeld": "% Held",
                "pctChange": "% Change"
            })
            
            sections.append("\nMUTUAL FUND HOLDERS")
            sections.append(tabulate(fund_df, headers="keys", tablefmt="grid", showindex=False))

        return "\n".join(sections)

    except Exception as e:
        return f"Error retrieving institutional holders for {ticker}: {str(e)}"

@mcp.tool()
async def get_earnings_history(ticker: str) -> str:
    """
    Retrieve and format the earnings history for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol (e.g., 'MSFT').

    Returns:
        str: A formatted table of earnings history data.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        earnings_history = ticker_obj.earnings_history

        if earnings_history.empty:
            return f"No earnings history data found for {ticker}"

        earnings_history = earnings_history.reset_index()
        return tabulate(earnings_history, headers="keys", tablefmt="grid", showindex=False)

    except Exception as e:
        return f"Error retrieving earnings history for {ticker}: {str(e)}"

@mcp.tool()
async def get_insider_trades(ticker: str) -> str:
    """
    Get recent insider trading activity.

    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL')

    Returns:
        str: Formatted table of insider trades with columns:
            - Date: Transaction date
            - Insider: Name of insider
            - Title: Position/title of insider
            - Transaction: Type of transaction
            - Shares: Number of shares
            - Value: Transaction value in USD
    """
    try:
        trades = yf.Ticker(ticker).insider_transactions

        if trades is None or trades.empty:
            return f"No insider trading data found for {ticker}"

        trades = trades.reset_index().rename(columns={"index": "Date"})
        trades["Date"] = pd.to_datetime(trades["Date"]).dt.strftime("%Y-%m-%d")
        if "Shares" in trades.columns:
            trades["Shares"] = trades["Shares"].apply(lambda x: f"{x:,.0f}")
        if "Value" in trades.columns:
            trades["Value"] = trades["Value"].apply(lambda x: f"${x:,.0f}")

        # Reorder columns if necessary
        columns_order = ["Date", "Insider", "Title", "Transaction", "Shares", "Value"]
        trades = trades[[col for col in columns_order if col in trades.columns]]

        return (
            f"Recent insider trades for {ticker}:\n\n"
            f"{tabulate(trades, headers='keys', tablefmt='grid', showindex=False)}"
        )

    except Exception as e:
        return f"Error retrieving insider trades for {ticker}: {str(e)}"


def main():
    try:
        logger.info("Running investor agent server...")
        mcp.run()
    except Exception as e:
        logger.error(f"Error in running server: {e}")
        sys.exit(1)