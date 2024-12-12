from modal import Function

functions: dict[str, Function | None] = {}
for key, lookup in {
    "get_news": ("news", "get_news"),
    "scrape_website": ("firecrawl-app", "scrape_website"),
    "get_top_trending_tickers": ("trending-stocks", "get_top_trending_tickers"),
    "generate_trending_summaries": ("trending-stocks", "generate_trending_summaries"),
    "add_to_watchlist": ("watchlist", "add_to_watchlist"),
    "fetch_fear_and_greed": ("fear-and-greed", "fetch_fear_and_greed"),
    "fetch_bitcoin_fear_and_greed": ("bitcoin-fear-and-greed", "fetch_bitcoin_fear_and_greed"),
    "get_crypto_funding_rates": ("crypto-funding-rates", "get_crypto_funding_rates"),
    "scrape_crypto_iv_rank": ("crypto-iv-rank", "scrape_crypto_iv_rank"),
    "get_options": ("options", "get_options"),
    "get_volatility_data": ("volatility-analysis", "get_volatility_data"),
    "get_market_metrics": ("tastytrade-client", "get_market_metrics"),
    "get_current_position_symbols": ("tastytrade-client", "get_current_position_symbols"),
    "get_ticker_analysis": ("ticker-analysis", "generate_investment_report"),
    "filter_interesting_tickers": ("ticker-analysis", "filter_interesting_tickers"),
    "reason_about_ticker": ("ticker-analysis", "reason_about_ticker"),
    "process_wsb_data": ("wsb-client", "process_wsb_data"),
    "analyze_market_with_tools": ("llm-with-tools", "analyze_market_with_tools"),
}.items():
    try:
        functions[key] = Function.lookup(lookup[0], lookup[1])
    except Exception:
        functions[key] = None

# Function schemas for LLM tool use (using anthropic schema format)
function_schemas = {
    "get_news": {
        "name": "get_news",
        "description": "Fetch recent news articles about a specific topic",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "The main topic or keyword to search for in news articles"
                },
                "search_description": {
                    "type": "string",
                    "description": "Additional context or keywords to refine the search",
                    "optional": True
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of news articles to return",
                    "optional": True,
                    "default": 10
                }
            },
            "required": ["search_term"]
        }
    },
    "scrape_website": {
        "name": "scrape_website",
        "description": "Scrapes a website URL and extracts its content, metadata, and a cleaned version of the main content using GPT-4.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the website to scrape"
                }
            },
            "required": ["url"]
        }
    },
    "get_top_trending_tickers": {
        "name": "get_top_trending_tickers",
        "description": "Fetch a list of the top trending stock tickers from social media platforms like WallStreetBets",
        "input_schema": {
            "type": "object",
            "properties": {
                "num_stocks": {
                    "type": "integer",
                    "description": "Number of trending stocks to return",
                    "default": 10,
                    "optional": True
                }
            },
            "required": []
        }
    },
    "get_options": {
        "name": "get_options",
        "description": "Retrieve a list of options with the highest open interest for a given ticker symbol",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker_symbol": {
                    "type": "string",
                    "description": "The ticker symbol of the stock"
                },
                "num_options": {
                    "type": "integer",
                    "description": "Number of top options to retrieve based on open interest",
                    "default": 10,
                    "optional": True
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date for option expiry filter (YYYY-MM-DD)",
                    "optional": True
                },
                "end_date": {
                    "type": "string",
                    "description": "End date for option expiry filter (YYYY-MM-DD)",
                    "optional": True
                },
                "strike_lower": {
                    "type": "number",
                    "description": "Lower bound for strike price",
                    "optional": True
                },
                "strike_upper": {
                    "type": "number",
                    "description": "Upper bound for strike price",
                    "optional": True
                },
                "option_type": {
                    "type": "string",
                    "description": "Filter by option type ('C' for calls, 'P' for puts)",
                    "enum": ["C", "P"],
                    "optional": True
                }
            },
            "required": ["ticker_symbol"]
        }
    },
    "get_volatility_data": {
        "name": "get_volatility_data",
        "description": "Fetches and processes volatility metrics for watchlist symbols and additional tickers, with optional IV rank filtering",
        "input_schema": {
            "type": "object",
            "properties": {
                "additional_tickers": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Additional ticker symbols to include regardless of metrics",
                    "optional": True
                },
                "iv_rank_below": {
                    "type": "number",
                    "description": "Include symbols with IV rank below this value (0-1)",
                    "optional": True
                },
                "iv_rank_above": {
                    "type": "number",
                    "description": "Include symbols with IV rank above this value (0-1)",
                    "optional": True
                }
            },
            "required": []
        }
    },
    "process_wsb_data": {
        "name": "process_wsb_data",
        "description": "Fetch and analyze recent WallStreetBets posts and comments",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "get_ticker_analysis": {
        "name": "get_ticker_analysis",
        "description": "Generate a comprehensive investment report for a specific ticker symbol",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker_to_research": {
                    "type": "string",
                    "description": "The ticker symbol to research (e.g., 'TSLA')"
                }
            },
            "required": ["ticker_to_research"]
        }
    }
}
