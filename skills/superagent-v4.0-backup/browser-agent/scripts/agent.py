"""
agent.py — minimal goal-driven loop that drives browser_engine.

Pattern: observe (page text) → decide (Claude returns ONE action as JSON) →
act (engine method) → repeat, until `done` or max_steps. Side-effectful actions
(extension approve / sign) go through a confirm gate — the operator decides,
never the page.

Anthropic import is guarded so this file compiles/imports without the SDK.
Wire `decide_with_claude` to your real key path, or pass your own `decide` fn.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from browser_engine import BrowserAgent, BrowserConfig

try:
    import anthropic  # type: ignore

    _SDK_OK = True
except ImportError:
    anthropic = None  # type: ignore
    _SDK_OK = False


# action JSON kontrak yang diharapkan dari model:
#   {"tool": "goto", "args": {"url": "..."}}
#   {"tool": "click_text", "args": {"text": "Connect"}}
#   {"tool": "approve_in_popup", "args": {"ext": "MetaMask", "button_text": "Connect"}}
#   {"tool": "done", "args": {"answer": "..."}}
_SAFE_TOOLS = {
    "goto",
    "read_text",
    "click_text",
    "fill",
    "discover_extensions",
    "open_popup",
    "eval_in_extension",
}
_GATED_TOOLS = {"approve_in_popup"}  # butuh konfirmasi operator


@dataclass
class AgentConfig:
    goal: str
    max_steps: int = 12
    model: str = "claude-opus-4-8"
    browser: BrowserConfig = field(default_factory=BrowserConfig)


DecideFn = Callable[[str, str], Awaitable[dict]]  # (goal, observation) -> action dict
ConfirmFn = Callable[[dict], Awaitable[bool]]  # (action) -> approved?


async def _default_confirm(action: dict) -> bool:
    print(f"[GATE] minta konfirmasi aksi: {action}")
    return False  # default aman: tolak. Override di pemanggil.


async def decide_with_claude(goal: str, observation: str, model: str) -> dict:
    """Tanya Claude satu aksi berikutnya. Return dict {tool, args}."""
    if not _SDK_OK:
        raise RuntimeError("anthropic SDK belum keinstall: pip install anthropic")
    client = anthropic.AsyncAnthropic()
    sys_prompt = (
        "You drive a browser to accomplish a goal. Reply with ONE action as raw JSON "
        '{"tool": <name>, "args": {...}}, no prose. Tools: goto, read_text, click_text, '
        "fill, discover_extensions, open_popup, eval_in_extension, approve_in_popup, done."
    )
    msg = await client.messages.create(
        model=model,
        max_tokens=300,
        system=sys_prompt,
        messages=[{"role": "user", "content": f"GOAL: {goal}\n\nPAGE:\n{observation[:6000]}"}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return json.loads(text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())


async def run(
    cfg: AgentConfig,
    decide: Optional[DecideFn] = None,
    confirm: ConfirmFn = _default_confirm,
) -> str:
    decide = decide or (lambda g, o: decide_with_claude(g, o, cfg.model))
    async with BrowserAgent(cfg.browser) as b:
        observation = "(blank page)"
        for step in range(cfg.max_steps):
            action = await decide(cfg.goal, observation)
            tool = action.get("tool")
            args = action.get("args", {}) or {}

            if tool == "done":
                return str(args.get("answer", "selesai"))
            if tool in _GATED_TOOLS and not await confirm(action):
                observation = f"(aksi '{tool}' ditolak operator)"
                continue
            if tool not in _SAFE_TOOLS and tool not in _GATED_TOOLS:
                observation = f"(tool tak dikenal: {tool})"
                continue

            method = getattr(b, tool)
            result = await method(**args)
            observation = await b.read_text() if tool != "read_text" else result
            observation = observation if isinstance(observation, str) else json.dumps(observation, default=str)
        return "(max_steps tercapai tanpa 'done')"


if __name__ == "__main__":
    print("agent.py: butuh browser_engine + (opsional) anthropic SDK untuk decide_with_claude.")
