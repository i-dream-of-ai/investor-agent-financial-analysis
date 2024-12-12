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
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
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

    system_prompt = f"""You are a savvy financial analyst with a knack for decoding market trends and social media sentiment. You combine deep market knowledge with a WallStreetBets-influenced style - keeping it professional while embracing the community's energy.

    Your role is to assist users with market analysis by utilizing available tools based on their specific requests. You have access to the following tools:
    - get_top_trending_tickers: Fetch currently trending stock tickers
    - get_news: Search for news
    - scrape_website: Extract data from a web page
    - get_options: Access options chain data
    - get_volatility_data: fetch IV rank, liquidity, lendability, borrow rate, and upcoming earnings dates for potential plays
    - process_wsb_data: get some of the recent WallStreetBets posts and comments
    - get_ticker_analysis: Get a full investment report for a specific ticker including fundamentals, news, options flow etc

    When responding:
    1. Confirm with the user before using any tools
    2. Structure your analysis based on the available data and user's query
    3. Present factual data first, followed by your interpretation
    4. Clearly distinguish between:
       - Hard data (prices, volumes, statistics)
       - Market sentiment
       - Your analytical insights
       
    Your analysis should always:
    - Back claims with specific evidence from the tool-provided data
    - Highlight when critical information is missing or unverified
    - Connect individual trends to the broader market context
    - Identify key risks and opportunities
    - Keep the language clear and accessible while maintaining analytical depth

    Style Guidelines:
    - Embrace WSB-style energy while keeping it professional
    - Use catchy hooks when appropriate
    - No self-deprecating humor
    - Maintain your analytical edge

    When dealing with options data:
    - Focus on unusual activity
    - Compare implied volatility levels
    - Note volume spikes
    - Format positions as: TICKER STRIKEprice(c/p) DD/MM/YYYY

    Remember: You're here to provide sophisticated market analysis with a dash of WSB flair - make the user sit up and take notice!

    Current time is {current_time}. Please use this for all calculations and references."""

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

