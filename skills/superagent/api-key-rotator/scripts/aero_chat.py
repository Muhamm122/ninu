#!/usr/bin/env python3
"""
aero_chat.py — Direct Aerolink Claude API chat wrapper.

Bypasses `hermes chat` (which auto-injects `extra_body.reasoning` that Aerolink
rejects with 400). Uses the Anthropic SDK directly.

Usage:
    python3 ~/.hermes/scripts/aero_chat.py "your prompt"
    python3 ~/.hermes/scripts/aero_chat.py --model claude-sonnet-4-6 "your prompt"
    python3 ~/.hermes/scripts/aero_chat.py --stream "your prompt"
    echo "prompt" | python3 ~/.hermes/scripts/aero_chat.py -

API key loaded from ~/.hermes/.env (ANTHROPIC_API_KEY) or first positional.
"""
import argparse
import os
import sys
from pathlib import Path

# Load ANTHROPIC_API_KEY from .env if not in env
def load_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or not key.startswith("aero_live_"):
        env_file = Path.home() / ".hermes" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY=") and "aero_live_" in line:
                    key = line.split("=", 1)[1].strip()
                    break
    return key

DEFAULT_BASE = "https://capi.aerolink.lat"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 4096

MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}

def main():
    p = argparse.ArgumentParser(description="Aerolink Claude API direct chat")
    p.add_argument("prompt", help="Prompt text (or '-' for stdin)")
    p.add_argument("--model", "-m", default=DEFAULT_MODEL, choices=list(MODELS.values()) + list(MODELS.keys()))
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--system", "-s", default="You are a helpful assistant.")
    p.add_argument("--stream", action="store_true", help="Stream output")
    p.add_argument("--base-url", default=DEFAULT_BASE)
    args = p.parse_args()

    # Resolve model alias
    if args.model in MODELS:
        args.model = MODELS[args.model]

    # Read prompt
    if args.prompt == "-":
        prompt = sys.stdin.read().strip()
    else:
        prompt = args.prompt

    key = load_key()
    if not key or not key.startswith("aero_live_"):
        print("ERROR: ANTHROPIC_API_KEY not found or invalid (must start with aero_live_)", file=sys.stderr)
        print("Set in ~/.hermes/.env or pass via env var", file=sys.stderr)
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic SDK not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=key, base_url=args.base_url)

    if args.stream:
        with client.messages.stream(
            model=args.model,
            max_tokens=args.max_tokens,
            system=args.system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                sys.stdout.write(text)
                sys.stdout.flush()
            print()  # newline at end
    else:
        r = client.messages.create(
            model=args.model,
            max_tokens=args.max_tokens,
            system=args.system,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in r.content:
            if block.type == "text":
                print(block.text)
        # Print usage to stderr
        if hasattr(r, "usage"):
            print(f"\n[usage] input={r.usage.input_tokens} output={r.usage.output_tokens}", file=sys.stderr)

if __name__ == "__main__":
    main()
