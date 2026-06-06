# 🤖 AI Agent — Educational Demo

A command-line agent that connects to **Food Ordering App** (via MCP) to find restaurants,
browse menus, and place orders — while exposing every internal component so
students can watch the agent *think* in real time.

---

## What you'll learn

| Component | File | Concept |
|-----------|------|---------|
| **Memory** | `memory.py` | How agents remember facts across turns |
| **Reasoning Loop** | `reasoning.py` | Think → Plan → Act → Observe → Answer |
| **MCP Server** | `mcp_server.py` | Exposes food-ordering tools over MCP |
| **MCP Client** | `mcp_client.py` | Calls the remote MCP server over HTTP |
| **Reasoning Loop** | `reasoning.py` | Think → Plan → Act → Observe → Answer |
| **LLM Client** | `llm.py` | Conversation history + system prompts |
| **Memory** | `memory.py` | How agents remember facts across turns |
| **Display** | `display.py` | Color-coded output for each component |
| **Entry point** | `agent.py` | The REPL loop that keeps the agent alive |

---

## Quick start

### 1. Install dependencies
```bash
pip install openai rich mcp
```

### 2. Set your API key
```bash
export OPENAI_API_KEY=sk-...
```

### 3. Start the MCP server
The client expects the MCP server to be running first.

```bash
cd src
python mcp_server.py
```

This starts the MCP HTTP endpoint on `http://127.0.0.1:8000/mcp` by default.

### 4. Run the agent
In a second terminal:

```bash
cd src
python agent.py
```

If your server is running somewhere else, set:

```bash
export MCP_SERVER_URL=http://your-host:port/mcp
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `quit` | Exit |
| `memory` | Show everything the agent has stored about you |
| `clear` | Clear conversation history (memory stays) |
| `reset` | Clear both history AND memory |
| `help` | Show all commands |

## Flags

| Flag | What it does |
|------|-------------|
| `--raw` | Also print the raw JSON from the LLM |
| `--debug` | Print full tracebacks on errors |

---

## Architecture

```
User message
     │
     ▼
┌──────────────────────────────────┐
│         Reasoning Loop           │
│                                  │
│  THINK   ← memory injected here  │
│    ↓                             │
│  PLAN    ← decides which tools   │
│    ↓                             │
│  ACT     ← calls MCP tools    │
│    ↓                             │
│  OBSERVE ← reads tool results    │
│    ↓                             │
│  ANSWER  ← composes reply        │
└──────────┬───────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
 Memory        MCP Server
(persists)     (tools + HTTP endpoint)

The agent then calls the MCP client in `mcp_client.py`, which talks to the
running MCP server over `MCP_SERVER_URL`.
```

---

## Try these prompts

```
Find me biryani near me
I'm vegetarian, what do you recommend?
Show me the menu at Hyderabadi Dum House
What have I ordered before?
Order butter chicken from the best place
```

After each message, watch:
- 🧠 **Memory panel** — new facts extracted from your message
- 🔵🟡🟠🟢✨ **Reasoning phases** — the agent's internal monologue
- 🔧 **Tool calls** — every MCP API call with exact inputs + results

---

## Key design patterns

### 1. Tool abstraction
The agent calls `execute_tool(name, input)` through `mcp_client.py`, which hides the
HTTP MCP transport details behind a simple adapter. This is the **adapter pattern**.

### 2. Structured output
The LLM always returns JSON (not plain text). This makes the output
machine-readable so `reasoning.py` can parse and route each component.

### 3. Memory injection
Before every API call, the current memory is formatted as a string and
injected into the system prompt. The LLM "knows" about the user without
any special memory API.

### 4. Reliable tool execution
The agent uses the MCP server as its real tool source, so tool calls run through
one consistent MCP interface. The server must be started before the agent begins.
