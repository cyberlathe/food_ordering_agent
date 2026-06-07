# 🤖 Food Ordering Agent

A command-line agent that combines an LLM, persistent memory, and an MCP-backed food-ordering tool server. It is designed for learning how agents reason, call tools, and remember user preferences across turns.

---

## What is included now

| Area | File | Notes |
|------|------|-------|
| REPL entry point | `src/agent.py` | Interactive chat loop with built-in commands |
| LLM wrapper | `src/llm.py` | Supports OpenAI and Anthropic providers |
| Reasoning loop | `src/reasoning.py` | Think → Plan → Act → Observe → Answer |
| MCP client | `src/mcp_client.py` | Calls the MCP server over HTTP |
| MCP server | `src/mcp_server.py` | Exposes mock food-ordering tools |
| Memory store | `src/memory.py` | Persists user facts to `src/memory.json` |
| Display layer | `src/display.py` | Color-coded reasoning, memory, and tool traces |

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your LLM credentials

OpenAI:

```bash
export OPENAI_API_KEY=sk-...
```

Anthropic:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Optional overrides:

```bash
export LLM_PROVIDER=openai      # or anthropic
export MODEL=gpt-5.4-mini        # or another supported model
export MAX_TOKENS=2048
```

### 3. Start the MCP server

From the project root:

```bash
python src/mcp_server.py
```

This serves the HTTP MCP endpoint on `http://127.0.0.1:8000/mcp` by default. You can override it with:

```bash
export MCP_SERVER_URL=http://your-host:port/mcp
export MCP_TRANSPORT=streamable-http
export MCP_MOUNT_PATH=/mcp
```

### 4. Run the agent

In a second terminal:

```bash
python src/agent.py
```

Useful flags:

```bash
python src/agent.py --raw
python src/agent.py --provider anthropic
python src/agent.py --debug
```

You can also enable raw JSON printing from the environment:

```bash
export SHOW_RAW_JSON=true
```

---

## Built-in commands

| Command | What it does |
|---------|-------------|
| `quit` / `exit` / `bye` | Exit the chat loop |
| `memory` | Show the persistent memory store |
| `history` | Show the recent chat history |
| `clear` | Clear only the conversation history |
| `reset` | Clear both history and memory |
| `help` | Show the command reference |

---

## Example prompts

```text
Find restaurants serving Italian or pizza
Show vegetarian menu items at Taco Fiesta
What are the top dishes at Olive & Spice?
Browse the menu at Sakura House and suggest something vegetarian
What have I ordered before?
```

As you chat, the app will show:
- 🧠 memory updates extracted from your messages
- 🔵🟡🟠🟢✨ the reasoning phases used by the agent
- 🔧 each MCP tool call and its summarized result

---

## Architecture

```text
User input
   ↓
REPL (src/agent.py)
   ↓
LLM client (src/llm.py)
   ↓
Reasoning loop (src/reasoning.py)
   ├─ memory injection
   ├─ tool planning
   └─ tool execution via MCP
   ↓
MCP server (src/mcp_server.py)
   ↓
Food-ordering tools + mock data
```

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

## Design notes

1. Structured JSON output
   The LLM returns JSON rather than free-form text so the reasoning loop can safely parse tool calls, memory updates, and the final reply.

2. Persistent memory
   Facts learned during the conversation are stored in `src/memory.json` and injected back into later prompts.

3. MCP-first tool execution
   The agent uses the MCP server as the canonical tool source, which makes tool behavior consistent and easy to inspect.

4. Provider switching
   The app can use OpenAI or Anthropic by setting `LLM_PROVIDER` and the matching API key.

