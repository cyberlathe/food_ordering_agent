"""
reasoning.py
------------
Runs the agent turn loop:
1. Ask the LLM what to do.
2. Execute requested tools.
3. Feed tool observations back to the LLM.
4. Repeat until the LLM can answer without repeating tool calls.
"""

import json
from typing import Any

import display as display
from config import SHOW_RAW_JSON
from mcp_client import execute_tool
from memory import Memory

MAX_TOOL_ROUNDS = 3


def run_turn(
    user_message: str,
    llm_client,
    memory: Memory,
) -> str:
    """Run one full reasoning loop turn and return the final reply."""
    memory_string = memory.to_prompt_string()
    parsed, _raw = llm_client.chat(user_message, memory_string)

    if SHOW_RAW_JSON:
        display.print_raw_json(parsed)
    _display_reasoning(parsed)

    all_memory_updates: list[dict[str, Any]] = []
    executed_calls: set[str] = set()

    for _round in range(MAX_TOOL_ROUNDS):
        all_memory_updates.extend(parsed.get("memory_updates", []))
        requested_tool_calls = parsed.get("tool_calls", [])
        tool_calls = _dedupe_tool_calls(requested_tool_calls, executed_calls)
        if not tool_calls:
            if requested_tool_calls:
                parsed, _raw = llm_client.observe_tools(
                    [_duplicate_tool_notice()],
                    memory.to_prompt_string(),
                )
                if SHOW_RAW_JSON:
                    display.print_raw_json(parsed)
                _display_reasoning(parsed)
                continue
            break

        round_results = _execute_tool_calls(tool_calls, executed_calls)
        parsed, _raw = llm_client.observe_tools(round_results, memory.to_prompt_string())

        if SHOW_RAW_JSON:
            display.print_raw_json(parsed)
        _display_reasoning(parsed)
    else:
        parsed["tool_calls"] = []
        parsed["reply"] = (
            "I have the tool results, but I stopped after several tool rounds "
            "to avoid repeating the same work. Please narrow the request if you "
            "need more detail."
        )

    all_memory_updates.extend(parsed.get("memory_updates", []))
    _apply_memory_updates(memory, all_memory_updates)

    reply = parsed.get("reply", "(no reply)")
    display.print_agent_reply(reply)
    return reply


def _display_reasoning(parsed: dict[str, Any]) -> None:
    reasoning_steps = parsed.get("reasoning", [])
    if reasoning_steps:
        display.print_reasoning_block(reasoning_steps)


def _dedupe_tool_calls(
    tool_calls: list[dict],
    executed_calls: set[str],
) -> list[dict]:
    pending = []
    for tc in tool_calls:
        tool_name = tc.get("tool", "")
        tool_input = tc.get("input", {})
        if not tool_name:
            continue

        signature = _tool_signature(tool_name, tool_input)
        if signature in executed_calls:
            continue

        pending.append(tc)
    return pending


def _execute_tool_calls(
    tool_calls: list[dict],
    executed_calls: set[str],
) -> list[dict]:
    round_results = []
    for tc in tool_calls:
        tool_name = tc.get("tool", "")
        tool_input = tc.get("input", {})
        signature = _tool_signature(tool_name, tool_input)
        executed_calls.add(signature)

        result_json = execute_tool(
            name=tool_name,
            input_data=tool_input,
        )

        try:
            result_data = json.loads(result_json.split("\n[fallback")[0])
            result_summary = _summarize_result(tool_name, result_data)
        except Exception:
            result_summary = result_json[:200]

        display.print_tool_call(
            tool=tool_name,
            input_data=tool_input,
            result_summary=result_summary
        )

        round_results.append({
            "tool": tool_name,
            "input": tool_input,
            "result": result_json,
            "summary": result_summary,
        })

    return round_results


def _duplicate_tool_notice() -> dict[str, str]:
    return {
        "tool": "system",
        "input": "{}",
        "result": json.dumps({
            "message": (
                "The requested tool call was already executed this turn. "
                "Use the earlier tool observations in the conversation to "
                "answer now instead of repeating the call."
            )
        }),
        "summary": "Skipped duplicate tool call.",
    }


def _apply_memory_updates(memory: Memory, updates: list[dict[str, Any]]) -> None:
    for update in updates:
        key = str(update.get("key", "")).strip()
        value = update.get("value", "")
        if not key:
            continue

        changed = memory.set(key, value)
        if changed:
            display.print_memory_update(key, value)


def _tool_signature(tool_name: str, tool_input: dict) -> str:
    return json.dumps(
        {"tool": tool_name, "input": tool_input},
        sort_keys=True,
        default=str,
    )


def _summarize_result(tool_name: str, data: dict) -> str:
    """Create a human-readable one-line summary of a tool result."""
    if tool_name == "get_restaurants_for_keyword":
        restaurants = data.get("restaurants") or []
        if restaurants:
            names = ", ".join(f"{r['name']} (id {r['id']})" for r in restaurants)
            return f"Found {len(restaurants)} restaurant(s): {names}"
        return "No restaurants found."

    if tool_name == "get_menu_items_listing":
        items = data.get("menu_items") or []
        if items:
            names = ", ".join(i["name"] for i in items)
            return f"{len(items)} item(s): {names}..."
        return "No menu items found."

    if tool_name == "get_restaurant_menu_by_categories":
        items = data.get("menu_items") or []
        return f"{len(items)} item(s) in category."

    if tool_name == "get_saved_addresses_for_user":
        addresses = data.get("addresses") or []
        if addresses:
            return f"{len(addresses)} address(es): {addresses[0].get('address', '')}"
        return "No saved addresses."

    if tool_name == "get_order_history":
        orders = data.get("orders") or []
        return f"{len(orders)} past order(s)."

    if tool_name == "create_cart":
        return f"Cart created: {data.get('cart_id')} - Rs. {data.get('total_amount')}"

    if tool_name == "checkout_cart":
        return f"Order placed: {data.get('order_id')} - {data.get('estimated_delivery')}"

    return str(data)[:120]
