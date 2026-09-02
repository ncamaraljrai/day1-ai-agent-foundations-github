"""Confirms the SDK is new enough and the API key works. Run this first."""

import inspect
import sys

import anthropic

# --- Check 1: is the SDK new enough for what these labs use? ---------------
# Every lab passes output_config to control effort. Older SDK versions reject
# it with a TypeError that gives no hint about the real cause, so check here
# rather than letting lab 1.2 fail confusingly.
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
accepted = inspect.signature(client.messages.create).parameters

missing = [p for p in ("output_config", "cache_control") if p not in accepted]
if missing:
    print(f"Your anthropic SDK is {anthropic.__version__}, which does not accept: "
          f"{', '.join(missing)}")
    print("Upgrade it:  pip install -U anthropic")
    sys.exit(1)

print(f"SDK {anthropic.__version__} — supports everything these labs need.")

# --- Check 2: does the API key work? --------------------------------------
response = client.messages.create(
    model="claude-opus-5",
    max_tokens=100,
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": "Reply with exactly: setup OK"}],
)

for block in response.content:
    if block.type == "text":
        print(block.text)

print(f"\nTokens used — input: {response.usage.input_tokens}, "
      f"output: {response.usage.output_tokens}")
