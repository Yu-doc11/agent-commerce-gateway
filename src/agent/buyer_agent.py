import os
import json
import uuid
from dotenv import load_dotenv
from groq import Groq

from src.agent.tools import (
    search_catalog,
    get_product_details,
    check_budget_remaining,
    create_order,
    get_order_status,
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the merchant catalog for products by name and optional max price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword, e.g. 'bottle'"},
                    # "max_price": {"type": "integer", "description": "Max price in paise (optional)"},
                    "max_price": {"type": ["integer", "null"], "description": "Max price in paise, or null if no limit"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get full details of a single product by its ID.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "integer"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_budget_remaining",
            "description": "Check how much budget is left in the current session.",
            "parameters": {
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Attempt to purchase a product. May be blocked, pending approval, or created depending on guardrails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "product_id": {"type": "integer"},
                    "quantity": {"type": "integer"},
                },
                "required": ["session_id", "product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Check the current status of a previously created order.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "search_catalog": search_catalog,
    "get_product_details": get_product_details,
    "check_budget_remaining": check_budget_remaining,
    "create_order": create_order,
    "get_order_status": get_order_status,
}


def run_buyer_agent(session_id: str, goal: str, max_steps: int = 8) -> list[dict]:
    """
    Runs the buyer agent loop: the LLM decides which tools to call,
    we execute them, and feed results back until it's done or max_steps hit.
    Returns a transcript of every step taken (for printing/demo purposes).
    """
    system_prompt = (
        "You are a buyer agent shopping on behalf of a user with a fixed budget. "
        f"Your session_id is '{session_id}'. Your goal is: {goal}. "
        "Use the tools available to search the catalog, check your budget, and place orders. "
        "Always check your remaining budget before making a purchase. "
        "Stop once your goal is reasonably fulfilled or your budget is nearly spent. "
        "Be concise in your reasoning."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please fulfill this shopping goal: {goal}"},
    ]

    transcript = []

    for step in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg)

        # If the model didn't call a tool, it's done reasoning — stop.
        if not msg.tool_calls:
            transcript.append({"type": "final_message", "content": msg.content})
            break

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            fn = TOOL_FUNCTIONS.get(fn_name)
            if fn is None:
                result = {"error": f"Unknown tool: {fn_name}"}
            else:
                result = fn(**fn_args)

            transcript.append({
                "type": "tool_call",
                "tool": fn_name,
                "arguments": fn_args,
                "result": result,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return transcript


if __name__ == "__main__":
    import sys
    from src.db.database import SessionLocal
    from src.db.models import AgentSession

    db = SessionLocal()
    session = AgentSession(
        id=str(uuid.uuid4()), goal="buy a water bottle and a phone stand",
        budget_total=100000, budget_spent=0, status="active",
    )
    db.add(session)
    db.commit()

    print(f"Session created: {session.id}\n")

    transcript = run_buyer_agent(session.id, session.goal)

    for step in transcript:
        print(json.dumps(step, indent=2))
        print("---")