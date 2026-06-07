"""
web_backend.py
--------------
Simple local backend for the visual food-ordering demo.

Serves the HTML demo at http://127.0.0.1:8765/ and exposes
POST /api/chat for the frontend to call the real MCP + LLM flow.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(__file__))

from llm import LLMClient
from memory import Memory
from mcp_client import execute_tool

HOST = os.getenv("DEMO_HOST", "127.0.0.1")
PORT = int(os.getenv("DEMO_PORT", "8765"))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = PROJECT_ROOT / "food_ordering_agent.html"
MAX_TOOL_ROUNDS = 3


class DemoBackendHandler(BaseHTTPRequestHandler):
    server_version = "FoodOrderingDemo/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._serve_file(HTML_FILE, "text/html; charset=utf-8")
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8") or "{}")
            message = str(payload.get("message", "")).strip()
            if not message:
                raise ValueError("message is required")

            response = run_turn(message)
            self._send_json(200, response)
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Keep the server log concise and readable.
        print(f"[demo-backend] {format % args}")

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        try:
            content = file_path.read_bytes()
        except FileNotFoundError:
            self._send_json(404, {"error": "Demo HTML not found"})
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()


def run_turn(user_message: str) -> dict[str, Any]:
    """Run one full turn using the real MCP + LLM flow and return structured JSON."""
    memory = Memory()
    llm = LLMClient()

    parsed, _raw = llm.chat(user_message, memory.to_prompt_string())
    all_memory_updates = list(parsed.get("memory_updates", []))
    executed_signatures: set[str] = set()
    tool_results: list[dict[str, Any]] = []

    for _round in range(MAX_TOOL_ROUNDS):
        requested_tool_calls = parsed.get("tool_calls", [])
        pending_calls = _dedupe_tool_calls(requested_tool_calls, executed_signatures)
        if not pending_calls:
            break

        for tool_call in pending_calls:
            tool_name = str(tool_call.get("tool", "")).strip()
            input_data = tool_call.get("input", {}) or {}
            if not isinstance(input_data, dict):
                input_data = {}

            signature = _tool_signature(tool_name, input_data)
            executed_signatures.add(signature)

            result_json = execute_tool(name=tool_name, input_data=input_data)
            try:
                result_data = json.loads(result_json.split("\n[fallback", 1)[0])
                summary = _summarize_result(tool_name, result_data)
            except Exception:
                summary = result_json[:200]

            tool_results.append({
                "tool": tool_name,
                "input": input_data,
                "result": result_json,
                "summary": summary,
            })

        parsed, _raw = llm.observe_tools(tool_results, memory.to_prompt_string())
        all_memory_updates.extend(parsed.get("memory_updates", []))

    for update in all_memory_updates:
        key = str(update.get("key", "")).strip()
        value = str(update.get("value", ""))
        if key:
            memory.set(key, value)

    return {
        "reasoning": parsed.get("reasoning", []),
        "memory_updates": all_memory_updates,
        "tool_calls": tool_results,
        "reply": parsed.get("reply", ""),
        "memory": memory.all(),
    }


def _dedupe_tool_calls(tool_calls: list[dict[str, Any]], executed_signatures: set[str]) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        tool_name = str(tool_call.get("tool", "")).strip()
        input_data = tool_call.get("input", {}) or {}
        if not tool_name:
            continue
        signature = _tool_signature(tool_name, input_data)
        if signature not in executed_signatures:
            pending.append(tool_call)
    return pending


def _tool_signature(tool_name: str, input_data: dict[str, Any]) -> str:
    return json.dumps({"tool": tool_name, "input": input_data}, sort_keys=True, default=str)


def _summarize_result(tool_name: str, data: dict[str, Any]) -> str:
    if tool_name == "get_restaurants_for_keyword":
        restaurants = data.get("restaurants") or []
        if restaurants:
            names = ", ".join(f"{item['name']} (id {item['id']})" for item in restaurants)
            return f"Found {len(restaurants)} restaurant(s): {names}"
        return "No restaurants found."

    if tool_name in {"get_menu_items_listing", "get_restaurant_menu_by_categories"}:
        items = data.get("menu_items") or []
        return f"{len(items)} item(s) returned."

    if tool_name == "get_order_history":
        orders = data.get("orders") or []
        return f"{len(orders)} past order(s)."

    if tool_name == "create_cart":
        return f"Cart created: {data.get('cart_id')} - Rs. {data.get('total_amount')}"

    if tool_name == "checkout_cart":
        return f"Order placed: {data.get('order_id')} - {data.get('estimated_delivery')}"

    return str(data)[:160]


def main() -> None:
    print(f"[demo-backend] Serving demo at http://{HOST}:{PORT}/")
    print("[demo-backend] Make sure the MCP server is already running on http://127.0.0.1:8000/mcp")
    with ThreadingHTTPServer((HOST, PORT), DemoBackendHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
