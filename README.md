# ☕ AI Basic Inventory Agent Loop

An AI-powered inventory management system for a coffee shop supply store with two physical locations. Built with **FastAPI** and a **manual Python AI agent loop** — no frameworks used.

Carla, the coffee shop owner, can talk to the system naturally — register deliveries, log sales, and ask about stock levels — all through a conversational CLI interface.

---

## How It Works

The system has two parts that work together:

### 1. REST API (`api/app.py`)
FastAPI server that manages inventory data stored in a `products.csv` file so everything persists between sessions.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/inventory` | GET | List all products with their IDs, names, quantities, and units |
| `/inventory` | POST | Add a new product (name, quantity, unit) → returns 201 |
| `/inventory/{id}` | PATCH | Update stock using a delta value (+ for incoming, − for outgoing) |
| `/inventory/alerts` | GET | Get products below a configurable threshold (default: 10) |

### 2. AI Agent (`agent.py`)
A Python agent that connects to an LLM (OpenAI-compatible API) and uses the REST endpoints as **tools**. The agent runs a **manual loop** — no LangChain, no LlamaIndex, no frameworks:

```
Observe (read user input)
  → Think (send to LLM with tool definitions)
    → Act (call the tool the LLM selected)
      → Update (inject the result back into context)
        → Repeat until the LLM gives a final response
```

#### Tools available to the LLM

| Tool | Description |
|------|-------------|
| `list_products` | View all products in inventory |
| `add_product` | Register a new product (name, quantity, unit) |
| `update_stock` | Update stock by product ID (+delta = received, −delta = sold) |
| `check_low_stock` | Find products below a quantity threshold |

### Conversation Log
Every event in the loop is appended to `conversation_log.csv` with four fields:

| Field | Description |
|-------|-------------|
| `actor` | `user`, `agent`, or `tool` |
| `message` | The text or result content of the event |
| `tool_call` | Name of the tool called (empty if not applicable) |
| `timestamp` | ISO 8601 datetime of the event |

The file is **append-only** — each session adds rows without overwriting previous sessions.

---

## Project Structure

```
.
├── agent.py                 # AI agent with manual agent loop
├── api/
│   ├── __init__.py          # API package marker
│   └── app.py               # FastAPI application
├── products.csv             # Inventory data (persistent, read/write by API)
├── conversation_log.csv     # Conversation log (append-only, auto-generated)
├── requirements.txt         # Python dependencies
├── .env                     # Environment configuration
├── .gitignore               # Ignored files
└── README.md                # This file
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

This installs **fastapi**, **uvicorn**, **httpx**, **pydantic**, and **python-dotenv**.

### 2. Create or edit `.env`

The project uses a `.env` file for configuration. Create one with the following variables:

```env
# LLM Configuration (OpenAI-compatible API)
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://llm.4geeks.ai
LLM_MODEL=online/openrouter/openai/gpt-6-luna

# Inventory API
API_BASE_URL=http://localhost:8000
```

You can point to any OpenAI-compatible endpoint (OpenAI, OpenRouter, Groq, local Ollama, etc.).

### 3. Seed data (optional)

The project includes a `products.csv` with 15 coffee shop items ready to use. You can edit it directly or add products through the agent.

---

## How to Run

### Step 1 — Start the API

Open a **first terminal** and launch the FastAPI server:

```bash
uvicorn api.app:APP --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 2 — Start the agent

In a **second terminal**, run the agent:

```bash
python agent.py
```

The agent will greet you:

```
☕ Coffee Shop Inventory Agent
========================================
Type your message to Carla's assistant, or type 'exit' / 'quit' to stop.
```

### Step 3 — Talk to Carla's assistant

Type natural-language messages. Here are examples of everything the system can do:

#### 📋 List all products
```
You: show me all products in inventory
```
→ Returns a table of all products with IDs, names, quantities, and units.

#### ⚠️ Check low-stock alerts
```
You: what products are running low?
```
→ Returns all products with quantity below the default threshold (10).

```
You: show me products with less than 5 units
```
→ Uses the threshold parameter dynamically.

#### 📦 Register a delivery (incoming stock)
```
You: we just received 30 units of oat milk
```
→ The agent looks up Oat Milk, finds its ID, and updates stock with +30.

#### 💰 Record a sale (outgoing stock)
```
You: we sold 12 bags of arabica today
```
→ The agent finds "Arabica Coffee - Single Origin" and updates stock with −12.

#### 🆕 Add a new product
```
You: add a new product: coconut milk, 20 liters
```
→ Creates a new product entry in inventory.

#### ❌ Stop the session
```
You: exit
```
or `quit` / `q` to exit.

---

## Development Notes

### API Design
- Products have an auto-incremented integer `id`
- Stock updates use a **delta** value: positive for incoming stock, negative for outgoing
- The API validates that stock never goes negative (returns HTTP 400 if it would)
- All endpoints return descriptive error messages and appropriate HTTP status codes

### Agent Design
- The agent loop is implemented from scratch in plain Python (~280 lines)
- Conversation history is kept in memory during a session for contextual reasoning
- The loop terminates cleanly when the LLM returns a final response with no pending tool calls
- A safety limit of 10 iterations prevents infinite loops
- The agent reads `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and `API_BASE_URL` from the environment

### Conversation Log
- Every user message, agent response, tool call, and tool result is logged to `conversation_log.csv`
- The CSV uses four fields: `actor`, `message`, `tool_call`, `timestamp`
- New sessions append to the existing file (never overwrites)

---

## Example Conversation Log

After a session, `conversation_log.csv` will contain entries like:

| actor | message | tool_call | timestamp |
|-------|---------|-----------|-----------|
| user | show me all products in inventory | | 2026-10-23T23:30:00+00:00 |
| agent | Calling tool: list_products | list_products | 2026-10-23T23:30:01+00:00 |
| tool | [{"id":1,"name":"Oat Milk","quantity":24,...}] | list_products | 2026-10-23T23:30:01+00:00 |
| agent | Here's the current inventory... | | 2026-10-23T23:30:03+00:00 |

---

## Test Results

The system was tested end-to-end with all three core scenarios:

| Scenario | Input | Result |
|----------|-------|--------|
| 📋 List products | `show me all products in inventory` | ✅ Returned table of 15 products |
| ⚠️ Low-stock alerts | `what products are running low?` | ✅ Identified 5 products below threshold |
| 📦 Register delivery | `we just received 30 units of oat milk` | ✅ Found product (ID 1), updated 24 → 54 liters |
| 💰 Record sale | `we sold 12 bags of arabica today` | ✅ Found product (ID 5), updated 6 → −6 (prevented negative) |
| 🆕 Add product | `add coconut milk, 20 liters` | ✅ Created new product with ID 16 |
| 📝 Conversation log | (automatic) | ✅ 14+ entries logged across all fields |

The agent correctly:
- Parsed natural language into structured tool calls
- Called `list_products` first to find product IDs before `update_stock`
- Handled errors gracefully (e.g., prevented negative stock)
- Maintained conversation context across multiple exchanges
