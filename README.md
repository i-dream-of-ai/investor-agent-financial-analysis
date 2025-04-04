# investor-agent: A Financial Analysis MCP Server

## Overview

The **investor-agent** is a Model Context Protocol (MCP) server that provides comprehensive financial insights and analysis to Large Language Models. It leverages real-time market data, news, and advanced analytics to help users obtain:

- Detailed ticker reports including company overview, news, key metrics, performance, dates, analyst recommendations, and upgrades/downgrades.
- Options data highlighting high open interest.
- Historical price trends for stocks.
- Essential financial statements (income, balance sheet, cash flow) formatted in millions USD.
- Up-to-date institutional ownership and mutual fund holdings.
- Earnings history and insider trading activity.

The server integrates with [yfinance](https://pypi.org/project/yfinance/) for market data retrieval.

Combine this with an MCP server for placing trades on a brokerage platform such as [tasty-agent](https://github.com/ferdousbhai/tasty-agent) to place trades on tastytrade platform. Make sure to also enable web search functionality if you would like to incoporate latest news in your analysis.

## Prerequisites

- **Python:** 3.12 or higher
- **Package Manager:** [uv](https://docs.astral.sh/uv/)

## Installation

First, install **uv** if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, you can run the **investor-agent** MCP server using `uvx`:

```bash
uvx investor-agent
```

## Tools

The **investor-agent** server comes with several tools to support financial analysis:

### Ticker Information

1. **`get_ticker_data`**
   - **Description:** Retrieves a comprehensive report for a given ticker symbol, including company overview, news, key metrics, performance, dates, analyst recommendations, and upgrades/downgrades.
   - **Input:**
     - `ticker` (string): Stock ticker symbol (e.g., `"AAPL"`).
   - **Return:** A formatted multi-section report.

2. **`get_available_options`**
   - **Description:** Provides a list of stock options with the highest open interest.
   - **Inputs:**
     - `ticker_symbol` (string): Stock ticker symbol.
     - `num_options` (int, optional): Number of options to return (default: 10).
     - `start_date` & `end_date` (string, optional): Date range in `YYYY-MM-DD` format.
     - `strike_lower` & `strike_upper` (float, optional): Desired strike price range.
     - `option_type` (string, optional): Option type (`"C"` for calls, `"P"` for puts).
   - **Return:** A formatted table of options data.

3. **`get_price_history`**
   - **Description:** Retrieves historical price data for a specific ticker.
   - **Inputs:**
     - `ticker` (string): Stock ticker symbol.
     - `period` (string): Time period (choose from `"1d"`, `"5d"`, `"1mo"`, `"3mo"`, `"6mo"`, `"1y"`, `"2y"`, `"5y"`, `"10y"`, `"ytd"`, `"max"`).
   - **Return:** A table showing price history.

### Financial Data Tools

1. **`get_financial_statements`**
   - **Description:** Fetches financial statements (income, balance, or cash flow) formatted in millions USD.
   - **Inputs:**
     - `ticker` (string): Stock ticker symbol.
     - `statement_type` (string): `"income"`, `"balance"`, or `"cash"`.
     - `frequency` (string): `"quarterly"` or `"annual"`.
   - **Return:** A formatted financial statement.

2. **`get_institutional_holders`**
   - **Description:** Retrieves details about major institutional and mutual fund holders.
   - **Input:**
     - `ticker` (string): Stock ticker symbol.
   - **Return:** Two formatted tables listing institutional and mutual fund holders.

3. **`get_earnings_history`**
   - **Description:** Retrieves a formatted table of earnings history.
   - **Input:**
     - `ticker` (string): Stock ticker symbol.
   - **Return:** A table displaying historical earnings data.

4. **`get_insider_trades`**
   - **Description:** Fetches the recent insider trading activity for a given ticker.
   - **Input:**
     - `ticker` (string): Stock ticker symbol.
   - **Return:** A formatted table showing insider trades.

## Usage with MCP Clients

To integrate **investor-agent** with an MCP client (for example, Claude Desktop), add the following configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "investor": {
        "command": "path/to/uvx/command/uvx",
        "args": ["investor-agent"],
    }
  }
}
```

## Debugging

You can leverage the MCP inspector to debug the server:

```bash
npx @modelcontextprotocol/inspector uvx investor-agent
```

For log monitoring, check the following directories:

- macOS: `~/Library/Logs/Claude/mcp*.log`
- Windows: `%APPDATA%\Claude\logs\mcp*.log`

## Development

For local development and testing:

1. Use the MCP inspector as described in the [Debugging](#debugging) section.
2. Test using Claude Desktop with this configuration:

```json
{
  "mcpServers": {
    "investor": {
      "command": "path/to/uv/command/uv",
      "args": ["--directory", "path/to/investor-agent", "run", "investor-agent"],
    }
  }
}
```

## License

This MCP server is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
