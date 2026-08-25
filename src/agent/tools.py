import requests

BASE_URL = "http://127.0.0.1:8000"


def search_catalog(query: str = "", max_price: int = None) -> list[dict]:
    """Search the merchant catalog. Returns matching products."""
    resp = requests.get(f"{BASE_URL}/catalog/products")
    products = resp.json()

    if query:
        products = [p for p in products if query.lower() in p["name"].lower()]
    if max_price:
        products = [p for p in products if p["price"] <= max_price]

    return products


def get_product_details(product_id: int) -> dict:
    """Get full details of a single product."""
    resp = requests.get(f"{BASE_URL}/catalog/products/{product_id}")
    return resp.json()


def check_budget_remaining(session_id: str) -> dict:
    """Check how much budget is left in the current session."""
    resp = requests.get(f"{BASE_URL}/agent/session/{session_id}")
    data = resp.json()
    remaining = data["budget_total"] - data["budget_spent"]
    return {"remaining": remaining, "total": data["budget_total"], "spent": data["budget_spent"]}


def create_order(session_id: str, product_id: int, quantity: int) -> dict:
    """Attempt to create an order. May be blocked, pending approval, or created."""
    resp = requests.post(
        f"{BASE_URL}/orders",
        params={"session_id": session_id, "product_id": product_id, "quantity": quantity},
    )
    return resp.json()


def get_order_status(order_id: str) -> dict:
    """Check the current status of an order."""
    resp = requests.get(f"{BASE_URL}/orders/{order_id}")
    return resp.json()