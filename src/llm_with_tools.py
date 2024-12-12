import os
import logging
from datetime import datetime
from typing import TypedDict, Literal
import json

from anthropic import Anthropic
from function_registry import functions, function_schemas


logging.basicConfig(level=logging.INFO)


llm_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


def analyze_market_with_tools(
    chat_history: list[ChatMessage],
    model: str = "claude-3-sonnet-20240229",
    max_tokens: int = 2000,
    temperature: float = 0.8,
) -> list[ChatMessage]:
    """Use Claude with tools to analyze market data and provide recommendations."""
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    tools = [
        function_schemas[name] for name in [
            "get_top_trending_tickers",
            "get_news",
            "scrape_website",
            "get_options",
            "get_volatility_data",
            "process_wsb_data",
            "get_ticker_analysis"
        ]
    ]

    system_prompt = f"""You are a savvy financial analyst with a knack for decoding market trends and social sentiment. Your mission is to break down market opportunities and craft killer analysis that'll help retail traders navigate the wild world of trading.

    You have access to several powerful tools to dig deep into market data:
    - get_top_trending_tickers: Spot which tickers are heating up on WallStreetBets 🔥
    - process_wsb_data: Get the freshest takes from the WSB hivemind
    - get_ticker_analysis: Get a full investment report with news, options flow, and analyst hot takes
    - get_volatility_data: Track IV rank, liquidity, lendability, borrow rate, and upcoming earnings dates for potential plays
    - get_news: Search for breaking market news
    - get_options: Get only the options chain data (when you don't need the full ticker analysis)
    - scrape_website: Scrape a website URL and extract its content, metadata, and a cleaned version of the main content using GPT-4.

    When breaking down market opportunities, follow this playbook:

    1. News Impact Breakdown:
       - Rate significant news items on a scale of 1-5 for market impact
       - Create sentiment scores (-5 to +5) for key stocks
       - Connect the dots between news and price action

    2. Options Flow Analysis:
       - Identify unusual options strategies and volume spikes
       - Track the most active strikes and expiration dates
       - Compare IV levels and spot potential volatility plays

    3. Market Sentiment Pulse Check:
       - Break down bullish and bearish arguments
       - Spot near-term catalysts and risks
       - Create an overall sentiment score (-10 to +10)

    4. Trade Setup Breakdown:
       - Drop specific position recommendations using format: TICKER STRIKEprice(c/p) DD/MM/YYYY
       - Example: SPY 425c 27/03/2024
       - Back up each play with solid data and catalysts

    Keep your analysis:
    - Clear and punchy, using bullet points for key insights
    - Backed by specific data and market signals
    - We're aiming for that WallStreetBets vibe, but keep it classy - no self-deprecating humor, and maintain your analytical edge!
    - Focused on actionable insights and specific setups

    Today's date is {today_date}. Please use this date for all calculations and references.
    """

    try:
        # input validation for last message
        if not chat_history[-1]["content"].strip():
            return [ChatMessage(role="assistant", content="Error: Please provide a valid query.")]

        generated_messages: list[ChatMessage] = []

        while True:
            response = llm_client.messages.create(
                model=model,
                system=system_prompt,
                tools=tools,
                messages=chat_history + generated_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            logging.info(f"Response received. Stop reason: {response.stop_reason}")
            
            if response.stop_reason == "tool_use":
                # Handle tool calls
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        
                        logging.info(f"Executing {tool_name} with args: {tool_input}")
                        
                        try:
                            tool_result = functions[tool_name].remote(**tool_input)
                            tool_result_json = json.dumps(tool_result, indent=2)
                            tool_results.append(ChatMessage(
                                role="user",
                                content=tool_result_json,
                            ))
                        except Exception as e:
                            logging.error(f"Error executing/formatting tool {tool_name}: {e}")
                
                generated_messages.extend(tool_results)
            else:
                generated_messages.append(ChatMessage(
                    role="assistant", 
                    content=response.content[0].text
                ))
                return generated_messages

    except Exception as e:
        error_msg = f"Error generating analysis: {str(e)}"
        logging.error(error_msg)
        return [ChatMessage(role="assistant", content=error_msg)]

