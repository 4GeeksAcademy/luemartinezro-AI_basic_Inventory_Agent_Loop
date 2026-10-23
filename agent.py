"""
AI Inventory Agent — Manual Agent Loop
========================================
A Python AI agent that connects to an LLM (OpenAI-compatible API) and uses
the Inventory REST API as its set of tools. Runs in a loop:

    Observe (read user input)
      → Think (send to LLM with tool definitions)
        → Act (call the tool the LLM selected)
          → Update (inject the result back into the LLM context)
            → Repeat until the LLM gives a final response.

Every event in the loop is logged to conversation_log.csv.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

LOG_FILE = "conversation_log.csv"

# ---------------------------------------------------------------------------
# Tool definitions  (sent to the LLM so it knows what it can call)
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "List all products currently in inventory, including their IDs, names, quantities, and units of measure.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_product",
            "description": "Add a new product to the inventory. Provide the product name, starting quantity, and unit of measure (e.g. units, kg, liters).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the product, e.g. 'Oat Milk'",
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Starting stock quantity (must be >= 0)",
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measure, e.g. 'units', 'kg', 'liters'",
                    },
                },
                "required": ["name", "quantity", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_stock",
            "description": "Update the stock quantity of an existing product by a delta value. Use a positive number for incoming stock (e.g. a delivery) and a negative number for outgoing stock (e.g. a sale).",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "The unique ID of the product to update",
                    },
                    "delta": {
                        "type": "number",
                        "description": "Stock change: positive for incoming stock, negative for outgoing. Example: +30 means received 30 units, -12 means sold 12 units.",
                    },
                },
                "required": ["product_id", "delta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_low_stock",
            "description": "Get a list of all products whose current stock quantity is below a given threshold. Use this to answer questions like 'what products are running low?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "integer",
                        "description": "Quantity threshold (default 10). Products with stock below this value will be returned.",
                    }
                },
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Logging helpers  (conversation_log.csv)
# ---------------------------------------------------------------------------

LOG_FIELDS = ["actor", "message", "tool_call", "timestamp"]


def _log_event(actor: str, message: str, tool_call: str = "") -> None:
    """Append a single event row to conversation_log.csv."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        # Write header only if file is empty
        if fh.tell() == 0:
            writer.writeheader()
        writer.writerow({
            "actor": actor,
            "message": message,
            "tool_call": tool_call,
            "timestamp": timestamp,
        })


# ---------------------------------------------------------------------------
# Tool-call dispatcher  (calls the actual Inventory API)
# ---------------------------------------------------------------------------


async def _call_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool by calling the corresponding Inventory API endpoint.
    Returns the JSON response body as a string."""
    url = API_BASE_URL.rstrip("/")

    if tool_name == "list_products":
        url += "/inventory"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10)
        return _format_response(resp)

    elif tool_name == "add_product":
        url += "/inventory"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=arguments, timeout=10)
        return _format_response(resp)

    elif tool_name == "update_stock":
        product_id = arguments.pop("product_id")
        url += f"/inventory/{product_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.patch(url, json=arguments, timeout=10)
        return _format_response(resp)

    elif tool_name == "check_low_stock":
        url += "/inventory/alerts"
        params = {}
        if "threshold" in arguments:
            params["threshold"] = arguments["threshold"]
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
        return _format_response(resp)

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _format_response(resp: httpx.Response) -> str:
    """Format an HTTP response into a readable string for the LLM."""
    if resp.is_success:
        body = resp.text
        return body
    else:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return json.dumps({"error": f"HTTP {resp.status_code}", "detail": detail})


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


async def _llm_chat(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Send a chat completion request to an OpenAI-compatible LLM API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }
    body = {
        "model": LLM_MODEL,
        "messages": messages,
        "tools": tools if tools else None,
        "tool_choice": "auto",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers=headers,
            json=body,
            timeout=60,
        )

    if not resp.is_success:
        raise RuntimeError(
            f"LLM API error: HTTP {resp.status_code} - {resp.text}"
        )

    return resp.json()


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


async def _run_agent_loop(user_input: str) -> str:
    """Run the full agent loop for a single user message.

    Returns the final textual response from the LLM.
    """
    # Log the user message
    _log_event("user", user_input)

    # --- Initialise / extend conversation history -------------------------
    # We keep the full conversation in memory so the LLM can reason about
    # prior exchanges.  The loop below appends each assistant + tool role
    # message so it persists across iterations for *this* invocation.
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a helpful inventory management assistant for a coffee shop supply store. "
                "Your role is to help Carla manage stock across two locations.\n\n"
                "You have access to the following tools:\n"
                "- list_products: View all products in inventory.\n"
                "- add_product: Register a new product.\n"
                "- update_stock: Update stock levels (positive delta = received stock, "
                "negative delta = sold/used stock).\n"
                "- check_low_stock: Find products running low.\n\n"
                "When a user tells you about a delivery, a sale, or asks about inventory, "
                "determine which tool to call and call it. "
                "Respond to the user in a friendly, conversational tone. "
                "Always confirm what you did after calling a tool.\n\n"
                "IMPORTANT: If a tool call returns an error, explain the issue to the user "
                "and suggest how to fix it."
            ),
        },
        {"role": "user", "content": user_input},
    ]

    iteration_limit = 10  # safety limit to prevent infinite loops
    final_response = ""

    for iteration in range(iteration_limit):
        # --- Think: call LLM -------------------------------------------------
        llm_response = await _llm_chat(messages, tools=TOOLS)
        choice = llm_response["choices"][0]
        message = choice["message"]

        # Add the assistant's response to conversation history
        messages.append(message)

        # Check if the LLM wants to call a tool
        if tool_calls := message.get("tool_calls"):
            for tc in tool_calls:
                function_name = tc["function"]["name"]
                try:
                    function_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    function_args = {}

                # Log the tool call
                _log_event("agent", f"Calling tool: {function_name}", function_name)

                # --- Act: call the actual API ---------------------------------
                result_str = await _call_tool(function_name, function_args)

                # Log the tool result
                _log_event("tool", result_str, function_name)

                # --- Update: inject result back into context ------------------
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_str,
                })
        else:
            # No tool calls → this is the final response from the LLM
            final_response = message.get("content", "")
            _log_event("agent", final_response)
            break
    else:
        # If we exhausted the iteration limit, synthesize a fallback message
        final_response = (
            "I'm sorry, I seem to be having trouble processing your request. "
            "Please try again or rephrase what you said."
        )
        _log_event("agent", final_response)

    return final_response


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

import asyncio


async def main() -> None:
    """Simple CLI interface for the agent."""
    print("☕ Coffee Shop Inventory Agent")
    print("=" * 40)
    print("Type your message to Carla's assistant, or type 'exit' / 'quit' to stop.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye! 👋")
            break

        response = await _run_agent_loop(user_input)
        print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())