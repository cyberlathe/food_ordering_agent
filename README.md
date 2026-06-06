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
| **Tools** | `tools.py` | How agents interact with external APIs |
| **LLM Client** | `llm.py` | Conversation history + system prompts |
| **Display** | `display.py` | Color-coded output for each component |
| **Entry point** | `agent.py` | The REPL loop that keeps the agent alive |

---

## Quick start

### 1. Install dependencies
```bash
pip install openai rich
```

### 2. Set your API key
```bash
export OPENAI_API_KEY=sk-...
```

### 3. Run
```bash
python agent.py
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
 Memory        Tools
(persists)     (MCP)
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
The agent calls `execute_tool(name, input)` — it never knows if the result comes from the MCP API, This is the **adapter pattern**.

### 2. Structured output
The LLM always returns JSON (not plain text). This makes the output
machine-readable so `reasoning.py` can parse and route each component.

### 3. Memory injection
Before every API call, the current memory is formatted as a string and
injected into the system prompt. The LLM "knows" about the user without
any special memory API.

### 4. Reliable tool execution
The agent uses the local MCP server as its real tool source, so tool calls
run consistently through the same MCP interface.
