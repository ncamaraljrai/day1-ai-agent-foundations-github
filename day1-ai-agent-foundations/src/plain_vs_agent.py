"""
Asks the *same* question with no tools available, so you can see exactly
what a single model call does when it lacks the facts.

Run this AFTER agent_loop.py so you can compare the two outputs.
"""

import anthropic

client = anthropic.Anthropic()

QUESTION = (
    "How many business days do we have left before the invoice for "
    "order #4471 goes overdue? Show your reasoning briefly."
)

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": QUESTION}],
    # Note: no `tools` argument. The model has no way to look anything up.
)

print("PLAIN CALL, NO TOOLS")
print("=" * 60)
for block in response.content:
    if block.type == "text":
        print(block.text)
print("=" * 60)
print(f"stop_reason: {response.stop_reason}")
print(f"tokens — input: {response.usage.input_tokens}, "
      f"output: {response.usage.output_tokens}")
