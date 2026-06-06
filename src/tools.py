"""
tools.py
--------
Handles all Food Ordering App MCP tool calls.
"""

import itertools
import json
import random
import sys
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.fastmcp import FastMCP

# Mock data

_MOCK_RESTAURANTS = [
    {
        "id": 1001,
        "name": "Aurora Bistro",
        "cuisine": "Italian, Pizza, Pasta",
        "rating": 4.5,
        "delivery_time_minutes": 35,
        "avg_price_for_two": 400,
        "address": "Soho, London",
    },
    {
        "id": 1002,
        "name": "Sakura House",
        "cuisine": "Japanese, Sushi, Ramen",
        "rating": 4.7,
        "delivery_time_minutes": 30,
        "avg_price_for_two": 450,
        "address": "Shibuya, Tokyo",
    },
    {
        "id": 1003,
        "name": "Taco Fiesta",
        "cuisine": "Mexican, Tacos, Burritos",
        "rating": 4.6,
        "delivery_time_minutes": 28,
        "avg_price_for_two": 380,
        "address": "Santa Fe, New Mexico",
    },
    {
        "id": 1004,
        "name": "Olive & Spice",
        "cuisine": "Mediterranean, Greek, Mezze",
        "rating": 4.4,
        "delivery_time_minutes": 33,
        "avg_price_for_two": 420,
        "address": "Plaka, Athens",
    },
    {
        "id": 1005,
        "name": "Golden Wok",
        "cuisine": "Chinese, Dim Sum, Noodles",
        "rating": 4.3,
        "delivery_time_minutes": 37,
        "avg_price_for_two": 390,
        "address": "Lan Kwai Fong, Hong Kong",
    },
]

_MOCK_MENU = {
    1001: [
        {"name": "Margherita Pizza", "price": 260, "rating": 4.6},
        {"name": "Truffle Mushroom Pasta", "price": 320, "rating": 4.7},
        {"name": "Chicken Alfredo", "price": 340, "rating": 4.5},
        {"name": "Caprese Salad", "price": 210, "rating": 4.4},
        {"name": "Tiramisu", "price": 180, "rating": 4.8},
    ],
    1002: [
        {"name": "Salmon Nigiri", "price": 340, "rating": 4.8},
        {"name": "Spicy Tuna Roll", "price": 290, "rating": 4.6},
        {"name": "Miso Ramen", "price": 310, "rating": 4.7},
        {"name": "Veg Tempura", "price": 240, "rating": 4.3},
        {"name": "Matcha Cheesecake", "price": 190, "rating": 4.5},
    ],
    1003: [
        {"name": "Chicken Tacos", "price": 240, "rating": 4.6},
        {"name": "Veg Burrito Bowl", "price": 220, "rating": 4.4},
        {"name": "Beef Enchiladas", "price": 280, "rating": 4.7},
        {"name": "Guacamole & Chips", "price": 170, "rating": 4.3},
        {"name": "Churros", "price": 160, "rating": 4.5},
    ],
    1004: [
        {"name": "Greek Mezze Platter", "price": 260, "rating": 4.5},
        {"name": "Falafel Wrap", "price": 200, "rating": 4.4},
        {"name": "Lemon Herb Chicken", "price": 300, "rating": 4.6},
        {"name": "Hummus & Pita", "price": 180, "rating": 4.3},
        {"name": "Baklava", "price": 170, "rating": 4.7},
    ],
    1005: [
        {"name": "Szechuan Chicken", "price": 260, "rating": 4.5},
        {"name": "Vegetable Chow Mein", "price": 220, "rating": 4.3},
        {"name": "Prawn Dumplings", "price": 290, "rating": 4.6},
        {"name": "Mango Pudding", "price": 150, "rating": 4.2},
        {"name": "Sesame Tofu", "price": 210, "rating": 4.4},
    ],
}

_MOCK_ADDRESSES = [
    {
        "id": "addr_001",
        "label": "Home",
        "address": "12 MG Road, Tilakwadi, Belagavi, KA 590006",
    }
]

_MOCK_ORDER_HISTORY = [
    {
        "order_id": "ORD-8821",
        "restaurant": "Aurora Bistro",
        "items": ["Margherita Pizza", "Caprese Salad"],
        "total": 470,
        "status": "Delivered",
        "date": "2025-05-28",
    },
    {
        "order_id": "ORD-7753",
        "restaurant": "Taco Fiesta",
        "items": ["Chicken Tacos x2"],
        "total": 480,
        "status": "Delivered",
        "date": "2025-05-15",
    },
]

_NON_VEG_KEYWORDS = (
    "chicken",
    "beef",
    "lamb",
    "mutton",
    "egg",
    "fish",
    "salmon",
    "tuna",
    "prawn",
    "shrimp",
    "anchovy",
    "bacon",
    "ham",
    "prosciutto",
    "meat",
)


def _with_veg_flags(items: list[dict]) -> list[dict]:
    return [{**item, "veg": _is_veg_item(item["name"])} for item in items]


def _is_veg_item(name: str) -> bool:
    normalized = name.lower()
    return not any(keyword in normalized for keyword in _NON_VEG_KEYWORDS)


def _menu_for_restaurant(res_id) -> list[dict]:
    return _with_veg_flags(_MOCK_MENU.get(res_id, _MOCK_MENU[1001]))


def _filter_menu(items: list[dict], input_data: dict) -> list[dict]:
    category = str(input_data.get("category", "")).lower()
    keyword = str(input_data.get("keyword", "")).lower()
    veg_only = input_data.get("veg_only")

    filtered = items
    if category:
        filtered = [item for item in filtered if category in item["name"].lower()]
    if keyword:
        filtered = [item for item in filtered if keyword in item["name"].lower()]
    if veg_only is True:
        filtered = [item for item in filtered if item["veg"]]
    if veg_only is False:
        filtered = [item for item in filtered if not item["veg"]]

    return filtered


def _mock_tool(name: str, input_data: dict) -> str:
    """Simulate a food order tool call locally."""
    if name == "get_saved_addresses_for_user":
        return json.dumps({"addresses": _MOCK_ADDRESSES})

    if name == "get_restaurants_for_keyword":
        keyword = input_data.get("keyword", "").lower()
        results = [
            r
            for r in _MOCK_RESTAURANTS
            if keyword in r["cuisine"].lower() or keyword in r["name"].lower()
        ] or _MOCK_RESTAURANTS[:3]
        return json.dumps({"restaurants": results})

    if name == "get_menu_items_listing":
        res_id = input_data.get("res_id")
        menu = _filter_menu(_menu_for_restaurant(res_id), input_data)
        return json.dumps({"menu_items": menu})

    if name == "get_restaurant_menu_by_categories":
        res_id = input_data.get("res_id")
        menu = _filter_menu(_menu_for_restaurant(res_id), input_data)
        return json.dumps({"menu_items": menu})

    if name == "get_order_history":
        return json.dumps({"orders": _MOCK_ORDER_HISTORY})

    if name == "create_cart":
        return json.dumps(
            {
                "cart_id": "cart_" + str(random.randint(1000, 9999)),
                "total_amount": random.randint(200, 600),
                "status": "created",
            }
        )

    if name == "checkout_cart":
        return json.dumps(
            {
                "order_id": "ORD-" + str(random.randint(1000, 9999)),
                "status": "placed",
                "estimated_delivery": "35-45 minutes",
            }
        )

    return json.dumps({"error": f"Unknown mock tool: {name}"})


_MCP_PROTOCOL_VERSION = "2025-06-18"
_MCP_FALLBACK_PROTOCOL_VERSION = "2025-03-26"
_MCP_CLIENT_INFO = {"name": "food_ordering_agent", "version": "1.0.0"}
_REQUEST_IDS = itertools.count(1)

mcp = FastMCP(
    name="food_ordering_tools",
    instructions="Provide food ordering tools for restaurant search, menu browsing, cart, order history, place order.",
)


@mcp.tool()
def get_saved_addresses_for_user() -> dict:
    return json.loads(_mock_tool("get_saved_addresses_for_user", {}))


@mcp.tool()
def get_restaurants_for_keyword(keyword: str) -> dict:
    return json.loads(_mock_tool("get_restaurants_for_keyword", {"keyword": keyword}))


@mcp.tool()
def get_menu_items_listing(res_id: int, category: str = "", keyword: str = "", veg_only: bool | None = None) -> dict:
    return json.loads(_mock_tool("get_menu_items_listing", {"res_id": res_id, "category": category, "keyword": keyword, "veg_only": veg_only}))


@mcp.tool()
def get_restaurant_menu_by_categories(res_id: int, category: str = "", keyword: str = "", veg_only: bool | None = None) -> dict:
    return json.loads(_mock_tool("get_restaurant_menu_by_categories", {"res_id": res_id, "category": category, "keyword": keyword, "veg_only": veg_only}))


@mcp.tool()
def get_order_history() -> dict:
    return json.loads(_mock_tool("get_order_history", {}))


@mcp.tool()
def create_cart() -> dict:
    return json.loads(_mock_tool("create_cart", {}))


@mcp.tool()
def checkout_cart() -> dict:
    return json.loads(_mock_tool("checkout_cart", {}))


def _mcp_result_to_json(result) -> str:
    if hasattr(result, "model_dump"):
        result = result.model_dump()

    if isinstance(result, dict):
        if result.get("structuredContent") is not None:
            return json.dumps(result["structuredContent"])

        content = result.get("content")
    else:
        content = getattr(result, "content", None)

    if not isinstance(content, list):
        if isinstance(result, dict):
            return json.dumps(result)
        return json.dumps({"result": result})

    values = []
    text_chunks = []
    for block in content:
        if isinstance(block, dict):
            if "data" in block:
                values.append(block["data"])
                continue

            if "text" in block:
                text = str(block["text"])
                try:
                    values.append(json.loads(text))
                except json.JSONDecodeError:
                    text_chunks.append(text)
                continue

        text_chunks.append(str(block))

    if len(values) == 1 and not text_chunks:
        return json.dumps(values[0])

    if values or text_chunks:
        return json.dumps({
            "content": values,
            "text": "\n".join(text_chunks).strip(),
        })

    return json.dumps(result)

async def _call_tool_via_mcp(name: str, input_data: dict) -> str:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).resolve())],
        cwd=str(Path(__file__).resolve().parent),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, input_data)
            return _mcp_result_to_json(result)


def execute_tool(
    name: str,
    input_data: dict,
    use_mock: bool,
) -> tuple[str, bool]:
    """Execute a food order agent tool via MCP, or fall back to mock data."""
    if use_mock:
        return _mock_tool(name, input_data), True

    try:
        result = anyio.run(_call_tool_via_mcp, name, input_data)
        return result, False
    except Exception:
        return _mock_tool(name, input_data), True


if __name__ == "__main__":
    mcp.run(transport="stdio")
