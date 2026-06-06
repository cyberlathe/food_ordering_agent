"""
memory.py
---------
The agent's memory: a simple key-value store that persists to disk.

CONCEPT FOR STUDENTS
--------------------
Memory lets the agent remember facts across turns so the user doesn't have to
repeat themselves. Example: once you say "I'm vegetarian", the agent stores
that and uses it in every future request.

There are many kinds of memory in AI agents:
  • Short-term / working memory  → the current conversation (handled by llm.py)
  • Long-term memory             → THIS FILE. Facts that survive across sessions.
  • External memory              → vector databases, SQL, etc. (not shown here)
"""

import json
import os
from datetime import datetime
from typing import Any

from config import MEMORY_FILE


class Memory:
    def __init__(self):
        self._store: dict[str, Any] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> bool:
        """Store a fact. Returns True if the value changed."""
        changed = self._store.get(key) != value
        if changed:
            self._store[key] = value
            self._store["__updated_at__"] = datetime.now().isoformat()
            self._save()
        return changed

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def all(self) -> dict[str, Any]:
        """Return all stored facts (excluding internal keys)."""
        return {k: v for k, v in self._store.items() if not k.startswith("__")}

    def clear(self):
        self._store = {}
        self._save()

    def to_prompt_string(self) -> str:
        """Format memory as a readable string for injection into the LLM prompt."""
        facts = self.all()
        if not facts:
            return "No facts stored yet."
        lines = [f"  • {k}: {v}" for k, v in facts.items()]
        return "\n".join(lines)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE) as f:
                    self._store = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._store = {}

    def _save(self):
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self._store, f, indent=2)
        except OSError:
            pass  # non-fatal; in-memory store still works
