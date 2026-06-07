"""
tools.py
--------
Handles all Food Ordering App MCP tool calls.
"""

import itertools
import os
import random
from urllib import error as urllib_error
from urllib import request as urllib_request

import anyio
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
        "address": "45 Mercer St, New York, NY 10013",
    },
    {
        "id": 1002,
        "name": "Sakura House",
        "cuisine": "Japanese, Sushi, Ramen",
        "rating": 4.7,
        "delivery_time_minutes": 30,
        "avg_price_for_two": 450,
        "address": "23 Lexington Ave, New York, NY 10010",
    },
    {
        "id": 1003,
        "name": "Taco Fiesta",
        "cuisine": "Mexican, Tacos, Burritos",
        "rating": 4.6,
        "delivery_time_minutes": 28,
        "avg_price_for_two": 380,
        "address": "88 E 10th St, New York, NY 10003",
    },
    {
        "id": 1004,
        "name": "Olive & Spice",
        "cuisine": "Mediterranean, Greek, Mezze",
        "rating": 4.4,
        "delivery_time_minutes": 33,
        "avg_price_for_two": 420,
        "address": "17 W 32nd St, New York, NY 10001",
    },
    {
        "id": 1005,
        "name": "Golden Wok",
        "cuisine": "Chinese, Dim Sum, Noodles",
        "rating": 4.3,
        "delivery_time_minutes": 37,
        "avg_price_for_two": 390,
        "address": "12 Broadway, New York, NY 10004",
    },
]

_MOCK_MENU = {
    1001: [
        {"name": "Margherita Pizza", "price": 260, "rating": 4.6},
        {"name": "Truffle Mushroom Pasta", "price": 320, "rating": 4.7},
        {"name": "Chicken Alfredo", "price": 340, "rating": 4.5},
        {"name": "Caprese Salad", "price": 210, "rating": 4.4},
        {"name": "Tiramisu", "price": 180, "rating": 4.8},
        {"name": "Diet Coke", "price": 150, "rating": 4.5},
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
        "address": "123 Broadway, New York, NY 10001",
    },
    {
        "id": "addr_002",
        "label": "Office",
        "address": "456 Park Ave, New York, NY 10022",
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


_MCP_PROTOCOL_VERSION = "2025-06-18"
_MCP_FALLBACK_PROTOCOL_VERSION = "2025-03-26"
_MCP_CLIENT_INFO = {"name": "food_ordering_agent", "version": "1.0.0"}
_REQUEST_IDS = itertools.count(1)

mcp = FastMCP(
    name="food_ordering_tools",
    instructions="Provide food ordering tools for restaurant search, menu browsing, cart, order history, place order.",
)


@mcp.tool(description="Return the saved delivery addresses for the current user.")
def get_saved_addresses_for_user() -> dict:
    """Return the saved delivery addresses for the current user."""
    return {"addresses": _MOCK_ADDRESSES}


@mcp.tool(description="Search restaurants by cuisine, dish, or restaurant name. Each result includes an id field; use that id as res_id for menu-related tools.")
def get_restaurants_for_keyword(keyword: str) -> dict:
    """Search restaurants by cuisine, dish, or restaurant name."""
    keyword = keyword.lower()
    results = [
        r
        for r in _MOCK_RESTAURANTS
        if keyword in r["cuisine"].lower() or keyword in r["name"].lower()
    ] or _MOCK_RESTAURANTS[:3]
    return {"restaurants": results}


@mcp.tool(description="List menu items for a restaurant. Use the res_id returned by get_restaurants_for_keyword as the restaurant identifier.")
def get_menu_items_listing(res_id: int, category: str = "", keyword: str = "", veg_only: bool | None = None) -> dict:
    """List menu items for a restaurant, optionally filtered by category, keyword, or vegetarian preference."""
    menu = _filter_menu(_menu_for_restaurant(res_id), {"category": category, "keyword": keyword, "veg_only": veg_only})
    return {"menu_items": menu}


@mcp.tool(description="Return the restaurant menu grouped by categories. Use the res_id returned by get_restaurants_for_keyword as the restaurant identifier.")
def get_restaurant_menu_by_categories(res_id: int, category: str = "", keyword: str = "", veg_only: bool | None = None) -> dict:
    """Return the restaurant menu grouped by categories, with optional filtering."""
    menu = _filter_menu(_menu_for_restaurant(res_id), {"category": category, "keyword": keyword, "veg_only": veg_only})
    return {"menu_items": menu}


@mcp.tool(description="Return the user's past order history.")
def get_order_history() -> dict:
    """Return the user's past order history."""
    return {"orders": _MOCK_ORDER_HISTORY}


@mcp.tool(description="Create a new cart for the current order session.")
def create_cart() -> dict:
    """Create a new cart for the current order session."""
    return {
        "cart_id": "cart_" + str(random.randint(1000, 9999)),
        "total_amount": random.randint(200, 600),
        "status": "created",
    }


@mcp.tool(description="Checkout the cart for the current order session.")
def checkout_cart(address: str | None = None) -> dict:
    """Checkout the cart for the current order session."""
    return {
        "order_id": "ORD-" + str(random.randint(1000, 9999)),
        "status": "placed",
        "estimated_delivery": "35-45 minutes",
        "delivery_address": str(address or "Mock Address"),
    }


def list_available_tools() -> list[dict]:
    """Return MCP tool metadata from the server definition."""

    async def _list_tools() -> list:
        return await mcp.list_tools()

    try:
        tools = anyio.run(_list_tools)
        return [
            {
                "name": getattr(item, "name", ""),
                "description": getattr(item, "description", "") or getattr(item, "title", ""),
                "inputSchema": getattr(item, "inputSchema", None),
            }
            for item in tools
        ]
    except Exception:
        return []


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    mount_path = os.getenv("MCP_MOUNT_PATH", "/mcp")
    mcp.run(transport=transport, mount_path=mount_path)
