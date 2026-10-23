[ROL]
You are a fullstack and software developer

[CONTEXT]

AI basic Inventory Agent Loop
## Your challenge

A small local business — a coffee shop supply store with two physical locations — is losing money. Not because sales are down, but because no one on the team can answer a simple question at any given moment: "Do we have enough of this product to cover the week?"

Stock is tracked in a shared spreadsheet that no one updates consistently. The owner, Carla, has reached out to you after seeing a demo of an AI assistant at a trade fair. She doesn't want a dashboard she has to maintain manually — she wants to be able to talk to a system and get answers. She also wants the system to act: register deliveries, log sales, and tell her when something is running low, all through natural language.

Your job is to build that system. It has two parts that must work together:

1. A REST API built with FastAPI that manages the inventory data. It exposes endpoints for listing products, registering new ones, updating stock levels, and retrieving low-stock alerts. Products are stored in a CSV file so the data persists between sessions.

2. An AI agent written in Python that connects to an LLM and uses your API as its set of tools. The agent runs in a loop — it receives a message from Carla, reasons about what action to take, calls the appropriate API endpoint as a tool, and responds with the result. Every step of that loop is logged to a separate conversation_log.csv file.

#### Complementary knowledge: the agent loop and tool calling

At this point in the course you know how to build a FastAPI and how to call an external API from Python. An AI agent adds one layer on top: instead of you deciding when to call which endpoint, the LLM decides. You describe your endpoints as tools — each with a name, a description, and its expected parameters — and the model selects the right one based on the user's message.

The loop follows this cycle:

Observe (read user input)
    → Think (send to LLM with tool definitions)
        → Act (call the tool the LLM selected)
            → Update (inject the result back into the LLM context)
                → Repeat until the LLM gives a final response

Your agent must implement this cycle in a single Python file (agent.py). It should keep the full message history in memory during a session so the LLM can reason about prior exchanges.

##### Conversation log

Every event in the loop must be appended to conversation_log.csv with these four fields:

Field	Description
actor	user, agent, or tool
message	The text or result content of the event
tool_call	Name of the tool called (empty if not applicable)
timestamp	ISO 8601 datetime of the event

This file is append-only. Each session adds rows — it does not overwrite previous sessions.

    Carla has shared the following requirements via email:

    "I need to be able to tell the system things like 'we just received 30 units of oat milk' or 'we sold 12 bags of arabica today'. It should understand me and update the stock. I also want to ask things like 'what products are running low?' and get a direct answer. Everything should feel like a conversation, not a form."

You have full creative freedom over the product catalog and data structure, as long as it supports names, quantities, and a unit of measure (units, kg, liters, etc.).

Build something Carla could actually use on Monday morning.

[OUTPUT]

### API (api/app.py)

- Create a FastAPI application that stores inventory data in a products.csv file
- GET /inventory -- returns the full product list
- POST /inventory -- adds a new product (name, quantity, unit)
- PATCH /inventory/{product_id} -- updates the stock of an existing product (accepts a delta value: positive for incoming stock, negative for outgoing)
- GET /inventory/alerts -- returns all products whose quantity is below a configurable threshold (default: 10 units)
- All endpoints must return appropriate HTTP status code and descriptive messages on error.

### Agent (agent.py)
- Define your API endpoints as tools for the LLM -- each tool must have a clear name, description, and typed parameters
- Implement the full agent loop: observe -> think -> Act -> update -> repeat
- The agent must keep the conversation history in memory for the duration of the session
- When the LLM selects a tool, the agent must call the corresponding API endpoint and inject the result back into the context
- The loop must terminate cleanly when the LLM returns a final response with no pending tool calls
- The agent must expose a simple CLI interface: it should read user input from the terminal and print the agent's response


### Conversatio log
- Every event (user message, agent response, tool, call, tool result) must be appended to conversation_log.csv
- The CSV must include the four required fields: actor, message, tool_call, timestamp
- The file must persist across sessions (append-only, never overwrite)

### General
- The API must be running before the agent starts. Document how to launch both in the README
- IMPORTANT: Do not use any agent framework (LangChain, LlamaIndex, AutoGen, etc). The agent loop must be implemented manually in plain python.

How to Submit

Push your repository to GitHub and share the link following your instructor's instructions. Make sure both api/app.py and agent.py are included, along with a brief note in your README on how to start both processes.

