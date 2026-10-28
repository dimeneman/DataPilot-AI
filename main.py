import sys
import logging
from langchain_core.messages import HumanMessage

# Import the compiled router graph
from agents.router_agent import data_agent

# Set up basic logging for the main execution
logging.basicConfig(level=logging.WARNING) 
logger = logging.getLogger("Main")

def print_separator(char="=", length=80):
    print(f"\n{char * length}\n")

def main():
    print_separator("=")
    print("🤖 Welcome to the AI Data Agent!")
    print("I can help you extract/transform data (ETL) or query your PostgreSQL database (SQL).")
    print("Type 'exit' or 'quit' to stop.")
    print_separator("=")

    while True:
        try:
            # 1. Get user input
            user_input = input("\n🧑 You: ").strip()

            if user_input.lower() in ['exit', 'quit']:
                print("\n👋 Goodbye!")
                break
                
            if not user_input:
                continue

            # 2. Prepare the initial state
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "route_response": ""
            }

            print("\n⏳ Agent is thinking...")

            # 3. Invoke the Data Agent (Router -> ETL/SQL)
            response = data_agent.invoke(initial_state)

            # 4. Extract and print the final response safely
            final_messages = getattr(response, "messages", []) if not isinstance(response, dict) else response.get("messages", [])
            
            print_separator("-")
            print("🤖 Agent:")
            if final_messages:
                content = final_messages[-1].content
                # Handle cases where Gemini returns a structured content block list
                if isinstance(content, list) and isinstance(content[0], dict) and "text" in content[0]:
                    print(content[0]["text"])
                else:
                    print(content)
            else:
                print("⚠️ No response generated.")
            print_separator("-")

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\n\n👋 Session interrupted. Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()