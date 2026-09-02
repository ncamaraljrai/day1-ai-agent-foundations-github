"""
Run the course labs against a local model via Ollama instead of a paid API.

Change ONE line in any lab script:

    # client = anthropic.Anthropic()
    from ollama_shim import OllamaAnthropic
    client = OllamaAnthropic(model="qwen2.5:7b")

Everything else in the script stays exactly the same. This class presents the
same surface the labs use: messages.create(...) returning an object with
.content blocks, .stop_reason and .usage, plus messages.count_tokens(...).

Requires:  ollama serve  (and a model that supports tool calling)
Uses only the standard library — no pip install needed.
"""

import json
import urllib.error
import urllib.request


# --- response objects shaped like the ones the labs already destructure ------

class TextBlock:
    type = "text"
    def __init__(self, text): self.text = text


class ToolUseBlock:
    type = "tool_use"
    def __init__(self, id, name, input): self.id, self.name, self.input = id, name, input


class Usage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        # Ollama has no prompt-caching surface, so these are always zero.
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0


class Response:
    def __init__(self, content, stop_reason, usage, model):
        self.content, self.stop_reason = content, stop_reason
        self.usage, self.model = usage, model
        self.stop_details = None


class TokenCount:
    def __init__(self, input_tokens): self.input_tokens = input_tokens


# --- the translation layer ---------------------------------------------------

class _Messages:
    def __init__(self, model, host, options):
        self.model, self.host, self.options = model, host, options
        self._tool_call_seq = 0

    def _post(self, path, payload):
        req = urllib.request.Request(
            self.host + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.host}. Is `ollama serve` running? ({exc})"
            ) from exc

    # -- Anthropic tool specs -> Ollama function specs ------------------------
    @staticmethod
    def _tools(specs):
        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                # Ollama calls the schema "parameters"; Anthropic "input_schema".
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        } for t in (specs or [])]

    # -- Anthropic message list -> Ollama message list -----------------------
    @staticmethod
    def _messages(messages, system):
        out = []
        if system:
            out.append({"role": "system", "content": system if isinstance(system, str)
                        else "\n".join(b.get("text", "") for b in system)})
        for m in messages:
            content = m["content"]
            if isinstance(content, str):
                out.append({"role": m["role"], "content": content})
                continue
            # A content-block list. Flatten it into what Ollama understands.
            texts, tool_calls = [], []
            for b in content:
                btype = b.get("type") if isinstance(b, dict) else getattr(b, "type", None)
                if btype == "text":
                    texts.append(b["text"] if isinstance(b, dict) else b.text)
                elif btype == "tool_use":
                    name = b["name"] if isinstance(b, dict) else b.name
                    args = b["input"] if isinstance(b, dict) else b.input
                    tool_calls.append({"function": {"name": name, "arguments": args}})
                elif btype == "tool_result":
                    # Ollama expects tool output as its own role:"tool" message.
                    out.append({"role": "tool",
                                "content": b["content"] if isinstance(b, dict) else b.content})
            if texts or tool_calls:
                msg = {"role": m["role"], "content": "\n".join(texts)}
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                out.append(msg)
        return out

    def create(self, *, messages, system=None, tools=None, model=None,
               max_tokens=None, output_config=None, cache_control=None, **_ignored):
        if cache_control is not None:
            raise NotImplementedError(
                "Ollama has no prompt-caching API, so cost_lab.py cannot run "
                "locally. That lab is Anthropic-API-only — read it instead."
            )

        options = dict(self.options)
        if max_tokens:
            options["num_predict"] = max_tokens

        data = self._post("/api/chat", {
            "model": self.model,          # the script's MODEL is ignored on purpose
            "messages": self._messages(messages, system),
            "tools": self._tools(tools),
            "stream": False,
            "options": options,
        })

        msg = data.get("message", {})
        blocks = []
        if msg.get("content"):
            blocks.append(TextBlock(msg["content"]))

        calls = msg.get("tool_calls") or []
        for c in calls:
            fn = c.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):        # some builds return a JSON string
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            self._tool_call_seq += 1
            # Ollama tool calls carry no id, so synthesise one. The labs only
            # require that the id we hand out comes back on the tool_result.
            blocks.append(ToolUseBlock(f"toolu_local_{self._tool_call_seq}",
                                       fn.get("name", ""), args))

        if not blocks:
            blocks.append(TextBlock(""))

        return Response(
            content=blocks,
            stop_reason="tool_use" if calls else "end_turn",
            usage=Usage(data.get("prompt_eval_count", 0), data.get("eval_count", 0)),
            model=data.get("model", self.model),
        )

    def count_tokens(self, *, messages, system=None, model=None, **_ignored):
        """Exact count via a zero-token generation: Ollama still reports how
        many prompt tokens it evaluated."""
        data = self._post("/api/chat", {
            "model": self.model,
            "messages": self._messages(messages, system),
            "stream": False,
            "options": {"num_predict": 0},
        })
        return TokenCount(data.get("prompt_eval_count", 0))


class OllamaAnthropic:
    """Drop-in stand-in for anthropic.Anthropic() backed by a local model."""

    def __init__(self, model="qwen2.5:7b", host="http://localhost:11434",
                 temperature=0.0):
        # temperature 0 makes the labs less noisy; raise it to see
        # non-determinism, which several exercises ask you to observe.
        self.messages = _Messages(model, host.rstrip("/"),
                                  {"temperature": temperature})
