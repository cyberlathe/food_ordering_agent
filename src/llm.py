"""
llm.py
------
Wraps the OpenAI API. Manages conversation history and asks the model for one
structured JSON object on every turn.
"""

import json
from typing import Any

from openai import OpenAI

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, LLM_PROVIDER, MAX_TOKENS, MODEL, OPENAI_API_KEY
from mcp_server import list_available_tools


SYSTEM_TEMPLATE = """You are an educational AI food agent connected to the Food Ordering App MCP platform.
You help users find restaurants, browse menus, and place food orders.

Your current memory (facts you have learned about this user):
{memory}

{tools}

Return exactly one JSON object with these fields:
- reasoning: five objects with phase and text for think, plan, act, observe, answer
- memory_updates: new user facts only, or []
- tool_calls: requested food ordering mcp tools, or []
- reply: a concise user-facing answer

Do not return markdown, code fences, commentary, or a second JSON object.
"""


AGENT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "food_agent_response",
        "strict": False,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reasoning", "memory_updates", "tool_calls", "reply"],
            "properties": {
                "reasoning": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["phase", "text"],
                        "properties": {
                            "phase": {
                                "type": "string",
                                "enum": ["think", "plan", "act", "observe", "answer"],
                            },
                            "text": {"type": "string"},
                        },
                    },
                },
                "memory_updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["key", "value"],
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                },
                "tool_calls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["tool", "input"],
                        "properties": {
                            "tool": {"type": "string"},
                            "input": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                        },
                    },
                },
                "reply": {"type": "string"},
            },
        },
    },
}


def _tool_prompt_block() -> str:
    tools = list_available_tools()
    if not tools:
        return "Available food ordering MCP tools: (tool discovery failed, so use the server-provided tool names when requested)."

    lines = ["Available food ordering MCP tools:"]
    for tool in tools:
        name = str(tool.get("name", "")).strip()
        description = str(tool.get("description", "")).strip() or "Tool provided by the MCP server."
        lines.append(f"- {name}: {description}")
    return "\n".join(lines)


class LLMClient:
    def __init__(self):
        self.provider = (LLM_PROVIDER or "openai").lower()

        if self.provider == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise ValueError(
                    "ANTHROPIC_API_KEY is not set.\n"
                    "  export ANTHROPIC_API_KEY=sk-ant-...\n"
                    "  or set it in config.py"
                )
            self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        else:
            if not OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY is not set.\n"
                    "  export OPENAI_API_KEY=sk-...\n"
                    "  or set it in config.py"
                )
            self.client = OpenAI(api_key=OPENAI_API_KEY)

        self.history: list[dict[str, str]] = []

    def chat(self, user_message: str, memory_string: str) -> tuple[dict[str, Any], str]:
        """Send a user message and current memory to the LLM."""
        self.history.append({"role": "user", "content": user_message})
        return self._complete(memory_string)

    def observe_tools(
        self,
        tool_results: list[dict[str, Any]],
        memory_string: str,
    ) -> tuple[dict[str, Any], str]:
        """Send tool observations back to the LLM so it can answer from facts."""
        observation = {
            "instruction": (
                "Use these tool results to answer the user's latest request. "
                "Do not repeat any tool call that already appears here unless "
                "different information is genuinely required."
            ),
            "tool_results": tool_results,
        }
        self.history.append({
            "role": "user",
            "content": "Tool observations:\n" + json.dumps(observation, indent=2),
        })
        return self._complete(memory_string)

    def _complete(self, memory_string: str) -> tuple[dict[str, Any], str]:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_TEMPLATE.format(
                    memory=memory_string,
                    tools=_tool_prompt_block(),
                ),
            },
            *self.history,
        ]

        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=messages[0]["content"],
                messages=messages[1:],
            )
            raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        else:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_completion_tokens=MAX_TOKENS,
                response_format=AGENT_RESPONSE_SCHEMA,
            )
            raw = response.choices[0].message.content or ""
        try:
            parsed = _normalize_response(_parse_single_json_object(raw))
        except (json.JSONDecodeError, ValueError):
            try:
                parsed = _normalize_response(_parse_first_json_object(raw))
            except (json.JSONDecodeError, ValueError):
                parsed = _fallback_response()
            raw = json.dumps(parsed)

        # Store only the natural reply in history. Replaying raw JSON encourages
        # later turns to echo previous structured objects.
        self.history.append({"role": "assistant", "content": parsed["reply"]})

        return parsed, raw

    def clear_history(self):
        """Reset conversation history, but not persistent memory."""
        self.history = []

    @property
    def turn_count(self) -> int:
        return len([m for m in self.history if m["role"] == "user"])


def _parse_single_json_object(raw: str) -> dict[str, Any]:
    """Parse exactly one JSON object and reject concatenated JSON output."""
    clean = _strip_code_fence(raw)
    decoder = json.JSONDecoder()
    parsed, end = decoder.raw_decode(clean)

    if not isinstance(parsed, dict):
        raise ValueError("Model response was JSON, but not an object.")

    if clean[end:].strip():
        raise ValueError("Model returned more than one JSON value.")

    return parsed


def _parse_first_json_object(raw: str) -> dict[str, Any]:
    """Recover the first object from an otherwise invalid model response."""
    clean = _strip_code_fence(raw)
    decoder = json.JSONDecoder()
    parsed, _ = decoder.raw_decode(clean)

    if not isinstance(parsed, dict):
        raise ValueError("Model response was JSON, but not an object.")

    return parsed


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _normalize_response(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "reasoning": _normalize_reasoning(parsed.get("reasoning", [])),
        "memory_updates": _normalize_memory_updates(parsed.get("memory_updates", [])),
        "tool_calls": _normalize_tool_calls(parsed.get("tool_calls", [])),
        "reply": _as_string(parsed.get("reply", "")),
    }


def _fallback_response() -> dict[str, Any]:
    return {
        "reasoning": [
            {"phase": "think", "text": "Received user message."},
            {"phase": "plan", "text": "The model response was not valid JSON."},
            {"phase": "act", "text": "Skipping tool calls."},
            {"phase": "observe", "text": "No usable structured output was returned."},
            {"phase": "answer", "text": "Asking the user to try again."},
        ],
        "memory_updates": [],
        "tool_calls": [],
        "reply": "I could not parse the model response cleanly. Please try again.",
    }


def _normalize_reasoning(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    steps: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        phase = _as_string(item.get("phase", "")).strip()
        text = _as_string(item.get("text", "")).strip()
        if phase and text:
            steps.append({"phase": phase, "text": text})
    return steps


def _normalize_memory_updates(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    updates: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        key = _as_string(item.get("key", "")).strip()
        update_value = _as_string(item.get("value", "")).strip()
        if key:
            updates.append({"key": key, "value": update_value})
    return updates


def _normalize_tool_calls(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    calls: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool = _as_string(item.get("tool", "")).strip()
        input_data = item.get("input", {})
        if tool:
            calls.append({
                "tool": tool,
                "input": input_data if isinstance(input_data, dict) else {},
            })
    return calls


def _as_string(value: Any) -> str:
    return value if isinstance(value, str) else str(value)
