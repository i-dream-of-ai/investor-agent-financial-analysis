from dotenv import load_dotenv
import os

from src.llm_with_tools import analyze_market_with_tools, ChatMessage

load_dotenv()

def main():
    """Main CLI interface for market analysis."""
    conversation_history = []

    while True:
        try:
            user_query = input("\nEnter your query (or 'quit' to exit): ")
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                break
                
            if not user_query.strip():
                print("Please enter a valid query.")
                continue
            
            conversation_history.append(ChatMessage(role="user", content=user_query))
            generated_messages = analyze_market_with_tools(conversation_history)
            conversation_history.extend(generated_messages)
            
            print(generated_messages[-1]["content"])
            print("\n" + "-"*80 + "\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()