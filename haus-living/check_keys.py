#!/usr/bin/env python3
"""Check which image generation API keys are available in the environment."""
import os
from pathlib import Path

# Load .env if present
env_path = Path.home() / ".hermes" / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

keys_to_check = [
    "FAL_KEY",
    "OPENAI_API_KEY", 
    "REPLICATE_API_TOKEN",
    "XAI_API_KEY",
    "KREA_API_KEY",
]

for k in keys_to_check:
    val = os.environ.get(k, "")
    if val:
        print(f"  ✓ {k} = {val[:8]}...{val[-4:]}")
    else:
        print(f"  ✗ {k} not set")
