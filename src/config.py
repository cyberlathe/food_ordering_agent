"""
config.py
---------
Central configuration for the agent.
Edit OPENAI_API_KEY here, or set it in the environment.
"""

import os

# ─── LLM provider ─────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
MODEL: str = os.getenv("MODEL", "gpt-5.4-mini")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2048"))

# ─── Memory ───────────────────────────────────────────────────────────────────
MEMORY_FILE: str = os.path.join(os.path.dirname(__file__), "memory.json")

# ─── Display ──────────────────────────────────────────────────────────────────
SHOW_RAW_JSON: bool = os.getenv("SHOW_RAW_JSON", "false").lower() in ("1", "true", "yes")

# ─── MCP client/server ───────────────────────────────────────────────────────
MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
