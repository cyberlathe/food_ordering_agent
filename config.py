"""
config.py
---------
Central configuration for the agent.
Edit OPENAI_API_KEY and USE_MOCK here, or set environment variables.
"""

import os

# ─── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "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")
MODEL: str = "gpt-5.4-mini"
MAX_TOKENS: int = 2048

# ─── Memory ───────────────────────────────────────────────────────────────────
MEMORY_FILE: str = os.path.join(os.path.dirname(__file__), "memory.json")

# ─── Display ──────────────────────────────────────────────────────────────────
SHOW_RAW_JSON: bool = os.getenv("SHOW_RAW_JSON", "false").lower() in ("1", "true", "yes")
