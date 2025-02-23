import logging
from datetime import datetime, timedelta

from src.investor_agent.server import (
    get_ticker_data,
    get_available_options,
    get_price_history,
    get_financial_statements,
    get_institutional_holders,
    get_earnings_history,
    get_insider_trades,
)

import src.investor_agent.yfinance_utils as yfinance_utils  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_company_overview(ticker="AAPL"):
    """Test company overview data retrieval"""
    logger.info("\n=== Testing Company Overview ===")
    overview = get_ticker_data(ticker)
    logger.info(overview)

def test_options_data(ticker="AAPL"):
    """Test options data retrieval"""
    logger.info("\n=== Testing Options Data ===")
    options = get_available_options(
        ticker,
        num_options=20,
        start_date=datetime.now().strftime("%Y-%m-%d"),
        end_date=(datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
    )
    logger.info(options)

def test_price_history(ticker="AAPL"):
    """Test price history retrieval"""
    logger.info("\n=== Testing Price History ===")
    history = get_price_history(ticker, period="1mo")
    logger.info(history)

def test_financial_statements(ticker="AAPL"):
    """Test financial statements retrieval"""
    logger.info("\n=== Testing Financial Statements ===")
    for statement_type in ["income", "balance", "cash"]:
        statements = get_financial_statements(ticker, statement_type, "quarterly")
        logger.info(f"\n{statement_type.upper()} STATEMENT:")
        logger.info(statements)

def test_institutional_holders(ticker="AAPL"):
    """Test institutional holders data retrieval"""
    logger.info("\n=== Testing Institutional Holders ===")
    holders = get_institutional_holders(ticker)
    logger.info(holders)

def test_earnings_history(ticker="AAPL"):
    """Test earnings history retrieval"""
    logger.info("\n=== Testing Earnings History ===")
    earnings = get_earnings_history(ticker)
    logger.info(earnings)

def test_insider_trades(ticker="AAPL"):
    """Test insider trades retrieval"""
    logger.info("\n=== Testing Insider Trades ===")
    trades = get_insider_trades(ticker)
    logger.info(trades)

if __name__ == "__main__":
    test_company_overview()
    test_options_data()
    test_price_history()
    test_financial_statements()
    test_institutional_holders()
    test_earnings_history()
    test_insider_trades()
