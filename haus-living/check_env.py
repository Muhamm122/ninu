#!/usr/bin/env python3
"""Quick check of available keys and modules."""
import os
import sys
from pathlib import Path

# Load .env
env_path = Path.home() / ".hermes" / ".env"
loaded = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                val = val.strip().strip('"').strip("'")
                loaded[key.strip()] = val
                os.environ.setdefault(key.strip(), val)

# Check keys
for k in ["FAL_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "KREA_API_KEY"]:
    v = os.environ.get(k, "")
    if v:
        print(f"KEY: {k} = {v[:8]}...{v[-4:]} (len={len(v)})")
    else:
        print(f"KEY: {k} = NOT SET")

# Check fal_client module
try:
    sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))
    from tools.fal_common import import_fal_client
    fc = import_fal_client()
    print(f"fal_client module: {fc}")
except Exception as e:
    print(f"fal_client import error: {e}")

# Check if there's a venv with fal
import subprocess
result = subprocess.run([sys.executable, "-c", "import fal_client; print('fal_client OK')"], 
                       capture_output=True, text=True)
print(f"fal_client in current python: {result.stdout.strip() or result.stderr.strip()}")

# Check hermes venv
hermes_venv = Path.home() / ".hermes" / "hermes-agent" / ".venv"
if hermes_venv.exists():
    pip = hermes_venv / "bin" / "pip"
    result2 = subprocess.run([str(pip), "list"], capture_output=True, text=True)
    for line in result2.stdout.splitlines():
        if "fal" in line.lower():
            print(f"Hermes venv package: {line}")
