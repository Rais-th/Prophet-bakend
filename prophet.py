#!/usr/bin/env python3
"""
🔮 ALPHA PROPHET CLI
An AI-powered warehouse optimization assistant
Built with Anthropic Claude API + v3.1 Smart Routing

Usage:
    python prophet.py              # Interactive mode
    python prophet.py -q "query"   # Single query mode
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, will use environment variables

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ Please install anthropic: pip install anthropic")
    sys.exit(1)

from cli.tools import TOOLS, execute_tool

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Print the Alpha Prophet banner"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
    ALPHA PROPHET - Warehouse Optimization
    ═══════════════════════════════════════
{Colors.END}
    Try: "I need 5000 units of N 14/146 DC"
         "Which warehouse for Texas?"
         "Show backlog summary"

    Type 'help' for more options, 'exit' to quit
"""
    print(banner)

def print_response(text: str):
    """Print AI response with formatting"""
    print(f"\n{Colors.GREEN}Prophet:{Colors.END} {text}\n")

def print_tool_call(tool_name: str, args: dict):
    """Print tool call info"""
    print(f"{Colors.YELLOW}[{tool_name}]{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}Error: {text}{Colors.END}")

def print_user_prompt():
    """Print user input prompt"""
    return input(f"{Colors.BLUE}{Colors.BOLD}You:{Colors.END} ")

class AlphaProphetCLI:
    """Alpha Prophet CLI - Natural language warehouse assistant"""

    def __init__(self, api_key: str = None):
        """Initialize the CLI with Anthropic client"""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

        if not self.api_key:
            print_error("ANTHROPIC_API_KEY not found!")
            print("Set it with: export ANTHROPIC_API_KEY='your-key'")
            print("Or pass it with: python prophet.py --api-key YOUR_KEY")
            sys.exit(1)

        self.client = Anthropic(api_key=self.api_key)
        self.conversation_history = []

        # System prompt for the AI
        from datetime import datetime
        today = datetime.now().strftime("%B %d, %Y")

        self.system_prompt = f"""You are Alpha Prophet, a warehouse optimization assistant.

TODAY'S DATE: {today}
Use this to understand "next quarter", "last year", "Q1 2026", etc.

STRICT RULES:
1. NEVER use emojis. Zero. None.
2. NEVER say "Great question!", "I'd be happy to", "Let me analyze". Just answer.
3. Answer first, explain after. Maximum 3-4 sentences unless showing data.
4. If you need info, make a reasonable assumption and state it.

CRITICAL BUSINESS CONTEXT:
- We have 3 warehouses ONLY: California, Houston, West Memphis
- EAST COAST WAREHOUSE DOES NOT EXIST
- If asked about East Coast, explain we don't have one. Suggest West Memphis serves East Coast states, or recommend evaluating a 3PL in NJ/PA area.
- West Memphis is the MAIN HUB (~70% of volume)
- Houston handles Texas only
- California handles CA, OR, WA, ID

RESPONSE FORMAT:
For distribution questions:
  West Memphis: 4,318 (86%)
  Houston: 568 (11%)
  California: 114 (3%)

For forecasts, give the number first:
  Q1 2026 Forecast: 1.2M units
  Based on: [brief reasoning]

For state questions:
  Texas -> Houston warehouse
  Reason: [one line]

DATA SOURCES (be specific when answering):
- SALES data (search_orders): Customer orders placed, 2023-Oct 2025
- FREIGHT data (search_freight): Actual shipments sent, 2024-Dec 2025
- BACKLOG: Open orders pending fulfillment

When asked "what happened on X date":
- For recent dates (Nov-Dec 2025): Use search_freight
- For older dates: Use search_orders
- Always tell user which data source you used

TOOLS: get_distribution, analyze_state, get_warehouse_info, get_backlog_summary, compare_routing, forecast_demand, recommend_east_coast_location, search_orders, search_freight

If a tool returns data, summarize it cleanly. Don't repeat the raw JSON."""

    def process_tool_calls(self, tool_calls: List) -> List[Dict]:
        """Process tool calls and return results"""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_input = tool_call.input

            print_tool_call(tool_name, tool_input)

            # Execute the tool
            result = execute_tool(tool_name, tool_input)

            results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": json.dumps(result, indent=2)
            })

        return results

    def _serialize_content(self, content) -> List[Dict]:
        """Convert API response content to serializable format"""
        serialized = []
        for block in content:
            if block.type == "text":
                serialized.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                serialized.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
        return serialized

    def chat(self, user_message: str) -> str:
        """Send a message and get a response"""

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        text_response = ""
        max_tool_rounds = 5  # Prevent infinite loops

        for _ in range(max_tool_rounds):
            # Call Claude API with tools
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=self.system_prompt,
                tools=TOOLS,
                messages=self.conversation_history
            )

            # Serialize and add assistant response to history
            assistant_content = self._serialize_content(response.content)
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_content
            })

            # Extract text from response
            for block in response.content:
                if block.type == "text":
                    text_response = block.text

            # If no tool calls, we're done
            if response.stop_reason != "tool_use":
                break

            # Process tool calls
            tool_calls = [b for b in response.content if b.type == "tool_use"]
            tool_results = self.process_tool_calls(tool_calls)

            # Add tool results to history
            self.conversation_history.append({
                "role": "user",
                "content": tool_results
            })

        # If no text response, provide fallback
        if not text_response.strip():
            text_response = "I couldn't generate a response. Please try rephrasing your question."

        return text_response

    def run_interactive(self):
        """Run in interactive REPL mode"""
        print_banner()

        while True:
            try:
                user_input = print_user_prompt()

                if not user_input.strip():
                    continue

                if user_input.lower() in ['exit', 'quit', 'q', 'bye']:
                    print(f"\n{Colors.CYAN}Goodbye.{Colors.END}\n")
                    break

                if user_input.lower() == 'clear':
                    self.conversation_history = []
                    print(f"{Colors.YELLOW}Conversation cleared.{Colors.END}")
                    continue

                if user_input.lower() == 'help':
                    self.print_help()
                    continue

                # Get AI response
                response = self.chat(user_input)
                print_response(response)

            except KeyboardInterrupt:
                print(f"\n\n{Colors.CYAN}Goodbye.{Colors.END}\n")
                break
            except Exception as e:
                print_error(str(e))

    def run_single_query(self, query: str):
        """Run a single query and exit"""
        response = self.chat(query)
        print_response(response)

    def print_help(self):
        """Print help information"""
        help_text = f"""
{Colors.CYAN}{Colors.BOLD}ALPHA PROPHET - HELP{Colors.END}

{Colors.YELLOW}Distribution:{Colors.END}
  "I need 5000 units of N 14/146 DC"
  "Distribute 10,000 insulators across warehouses"

{Colors.YELLOW}State Analysis:{Colors.END}
  "Which warehouse for Texas?"
  "What states does West Memphis cover?"

{Colors.YELLOW}Backlog:{Colors.END}
  "Show backlog summary"
  "What's pending for Q1?"

{Colors.YELLOW}Search Orders:{Colors.END}
  "Show Anixter orders from 2024"
  "What did Graybar order last quarter?"

{Colors.YELLOW}Optimization:{Colors.END}
  "Compare current vs optimal routing"
  "Where should we open an East Coast warehouse?"

{Colors.YELLOW}Commands:{Colors.END}
  help  - This help
  clear - Reset conversation
  exit  - Quit
"""
        print(help_text)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="🔮 Alpha Prophet - AI Warehouse Optimization Assistant"
    )
    parser.add_argument(
        "-q", "--query",
        help="Single query mode - ask a question and exit"
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )

    args = parser.parse_args()

    # Initialize CLI
    cli = AlphaProphetCLI(api_key=args.api_key)

    if args.query:
        # Single query mode
        cli.run_single_query(args.query)
    else:
        # Interactive mode
        cli.run_interactive()


if __name__ == "__main__":
    main()
