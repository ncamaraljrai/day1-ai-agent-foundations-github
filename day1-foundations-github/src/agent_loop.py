"""
A minimal but complete agent loop.

The task: answer "how many business days until invoice #4471 is overdue?"
No single model call can answer this — the model does not know the order,
does not know today's date, and does not know the holiday calendar. So we
give it three tools and let it work the problem out step by step.

Run:  python agent_loop.py
"""

import datetime
import json

import anthropic

client = anthropic.Anthropic()

MODEL = "claude-opus-5"
MAX_STEPS = 8  # hard ceiling on loop iterations — never omit this


# ---------------------------------------------------------------------------
# 1. THE TOOLS — ordinary Python functions. Nothing special about them.
# ---------------------------------------------------------------------------

# Pretend order database. In a real system this would be a SQL query.
ORDERS = {
    "4471": {"invoiced": "2026-03-03", "terms_days": 30, "customer": "Northwind Ltd"},
    "4472": {"invoiced": "2026-03-18", "terms_days": 14, "customer": "Acme Corp"},
}

# Pretend holiday calendar for one region. Note 2026-03-30 is a Monday, so it
# genuinely removes a working day — a "holiday" that falls on a weekend would
# change nothing and would make this example silently pointless.
HOLIDAYS = {"2026-03-30", "2026-04-06", "2026-05-01"}


def lookup_order(order_id: str) -> dict:
    """Return the invoice date and payment terms for an order."""
    order = ORDERS.get(order_id)
    if order is None:
        # Tools should fail informatively. This message goes back to the model
        # as an observation, so it can recover instead of guessing.
        return {"error": f"No order with id {order_id}. Known ids: {sorted(ORDERS)}"}
    return order


def get_today() -> dict:
    """Return today's date. The model cannot know this on its own."""
    return {"today": datetime.date.today().isoformat()}


def count_business_days(start: str, end: str) -> dict:
    """Count working days between two ISO dates, excluding weekends and holidays."""
    try:
        current = datetime.date.fromisoformat(start)
        finish = datetime.date.fromisoformat(end)
    except ValueError as exc:
        return {"error": f"Dates must be ISO format (YYYY-MM-DD): {exc}"}

    if finish < current:
        return {"error": f"end ({end}) is before start ({start})"}

    days = 0
    while current < finish:
        current += datetime.timedelta(days=1)
        is_weekend = current.weekday() >= 5          # 5 = Saturday, 6 = Sunday
        is_holiday = current.isoformat() in HOLIDAYS
        if not is_weekend and not is_holiday:
            days += 1
    return {"business_days": days}


# Maps the tool names the model will use to the functions above.
TOOL_FUNCTIONS = {
    "lookup_order": lookup_order,
    "get_today": get_today,
    "count_business_days": count_business_days,
}


# ---------------------------------------------------------------------------
# 2. THE TOOL DEFINITIONS — how the tools are described *to the model*.
#    The description is a prompt. Write it for the model, not for a human
#    reading your source code. Say when to use the tool, not just what it is.
# ---------------------------------------------------------------------------

TOOL_SPECS = [
    {
        "name": "lookup_order",
        "description": (
            "Look up an order by its id. Returns the invoice date (ISO format) "
            "and the payment terms in days. Call this whenever you need to know "
            "when an order was invoiced or what its terms are."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order id, e.g. '4471'.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_today",
        "description": (
            "Return today's date in ISO format. Call this whenever a calculation "
            "depends on the current date. Do not guess today's date."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "count_business_days",
        "description": (
            "Count working days between two ISO dates, excluding weekends and "
            "public holidays. The count excludes the start date and includes "
            "the end date. Use this instead of counting days yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "description": "Start date, YYYY-MM-DD."},
                "end": {"type": "string", "description": "End date, YYYY-MM-DD."},
            },
            "required": ["start", "end"],
        },
    },
]


# ---------------------------------------------------------------------------
# 3. THE LOOP — reason, act, observe, repeat.
# ---------------------------------------------------------------------------

def run_agent(goal: str) -> str:
    # `messages` is the agent's working memory. It grows every iteration, and
    # the whole thing is re-sent to the model each time.
    messages = [{"role": "user", "content": goal}]

    for step in range(1, MAX_STEPS + 1):
        print(f"\n{'=' * 60}\nSTEP {step}\n{'=' * 60}")

        # --- REASON: the model looks at the history and decides what to do.
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,          # a ceiling, not a cost — you are billed
                                       # only for tokens actually generated
            output_config={"effort": "low"},   # cheap setting; fine for this task
            tools=TOOL_SPECS,
            messages=messages,
        )

        # Show any commentary the model wrote alongside its decision.
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"[model says] {block.text.strip()}")

        # The model signals "I am done" via stop_reason. It owns this decision —
        # that is exactly what autonomy means in practice.
        if response.stop_reason != "tool_use":
            final = "".join(b.text for b in response.content if b.type == "text")
            print(f"\n{'*' * 60}\nFINAL ANSWER\n{'*' * 60}\n{final.strip()}")
            return final.strip()

        # Append the model's turn *unchanged* before adding results. Passing the
        # full `response.content` back is required — it carries the tool_use
        # blocks the results must match, plus any internal blocks the model
        # needs on the next turn.
        messages.append({"role": "assistant", "content": response.content})

        # --- ACT: run each requested tool. Note that YOUR code does this, not
        #     the model. The model only ever asked.
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            print(f"[action]  {block.name}({json.dumps(block.input)})")
            function = TOOL_FUNCTIONS.get(block.name)
            if function is None:
                output = {"error": f"Unknown tool: {block.name}"}
            else:
                try:
                    output = function(**block.input)
                except Exception as exc:  # noqa: BLE001 - report, never crash the loop
                    output = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"[result]  {json.dumps(output)}")

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,       # must match the request's id
                "content": json.dumps(output),
                "is_error": "error" in output,
            })

        # --- OBSERVE: results go back as a user turn, and the loop continues.
        #     All results from one assistant turn go in ONE message.
        messages.append({"role": "user", "content": results})

    print("\nStopped: hit the step limit without reaching an answer.")
    return "Stopped: step limit reached"


if __name__ == "__main__":
    run_agent(
        "How many business days do we have left before the invoice for "
        "order #4471 goes overdue? Show your reasoning briefly."
    )
