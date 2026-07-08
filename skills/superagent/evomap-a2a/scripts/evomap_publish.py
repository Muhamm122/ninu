#!/usr/bin/env python3
"""
EvoMap A2A asset publisher — Gene + Capsule + EvolutionEvent bundle.
Reads credentials from ~/.evomap/ and publishes via Tor.

Usage:
  python3 evomap_publish.py                    # Validate + publish
  python3 evomap_publish.py --validate-only    # Validate only (dry run)
  python3 evomap_publish.py --max-retries 5    # Override retry count
"""
import json, subprocess, os, hashlib, time, argparse

# === CONFIG ===
SECRET_PATH = os.path.expanduser("~/.evomap/node_secret")
NODE_ID_PATH = os.path.expanduser("~/.evomap/node_id")

def load_creds():
    secret = open(SECRET_PATH).read().strip()
    node_id = open(NODE_ID_PATH).read().strip()
    return node_id, secret

def compute_id(obj):
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    h = hashlib.sha256(canonical.encode()).hexdigest()
    return f"sha256:{h}"

def api_post(path, body, secret, max_retries=3):
    url = f"https://evomap.ai{path}"
    data = json.dumps(body).encode()
    for attempt in range(max_retries):
        result = subprocess.run(
            ["torsocks", "curl", "-s", "-m", "25", "-X", "POST", url,
             "-H", "Authorization: Bearer *** + secret,
             "-H", "Content-Type: application/json",
             "-d", data],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                r = json.loads(result.stdout)
                if r.get("error") == "server_busy":
                    wait = r.get("retry_after_ms", 3000) / 1000
                    print(f"  server_busy, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                return r
            except json.JSONDecodeError:
                return {"error": "json_parse_error", "raw": result.stdout[:200]}
        else:
            print(f"  Request failed (attempt {attempt+1}): {result.stderr[:100]}")
            time.sleep(5)
    return {"error": "max_retries_exceeded"}

def build_bundle(gene_data, capsule_data, event_data):
    """Build complete Gene+Capsule+EvolutionEvent bundle with cross-references."""
    # Step 1: Compute Gene ID
    gene_id = compute_id(gene_data)
    gene_data["asset_id"] = gene_id

    # Step 2: Cross-ref Capsule → Gene, compute Capsule ID
    capsule_data["gene"] = gene_id
    capsule_id = compute_id(capsule_data)
    capsule_data["asset_id"] = capsule_id

    # Step 3: Cross-ref Event → Capsule + Gene, compute Event ID
    event_data["capsule_id"] = capsule_id
    event_data["genes_used"] = [gene_id]
    event_id = compute_id(event_data)
    event_data["asset_id"] = event_id

    return [gene_data, capsule_data, event_data]

def make_envelope(node_id, message_type, assets):
    return {
        "protocol": "gep-a2a",
        "protocol_version": "1.0.0",
        "message_type": message_type,
        "message_id": f"msg_{int(time.time() * 1000)}_{os.urandom(4).hex()}",
        "sender_id": node_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": {"assets": assets}
    }

# === EXAMPLE BUNDLE (IDX Portfolio Monitor) ===
def example_bundle():
    gene = {
        "type": "Gene",
        "schema_version": "1.5.0",
        "category": "optimize",
        "signals_match": ["portfolio tracking", "dividend investing", "stock analysis"],
        "summary": "Automated Indonesian stock portfolio management with yfinance, technical indicators, and Telegram alerts for IDX dividend/value investing.",
        "validation": ["python3 -c \"import yfinance; print('ok')\""]
    }
    capsule = {
        "type": "Capsule",
        "schema_version": "1.5.0",
        "trigger": ["portfolio tracking", "dividend investing", "stock analysis"],
        "summary": "Automated Python pipeline for monitoring IDX stock portfolio with yfinance, mplfinance charts, and Telegram alert automation for dividend tracking.",
        "content": "Intent: Build automated IDX portfolio monitoring.\n\nStrategy:\n1. Pull prices from yfinance for IDX tickers\n2. Calculate RSI, MACD, Bollinger Bands, SMA, Pivot Points\n3. Generate candlestick charts with mplfinance\n4. Send daily briefings to Telegram at 15:30 WIB\n5. Track unrealized P/L, yield on cost, dividends\n\nScope: 4 file(s), 250 line(s)\n\nOutcome score: 0.92",
        "strategy": [
            "Pull real-time stock prices from yfinance",
            "Calculate technical indicators for entry/exit signals",
            "Generate candlestick charts with support/resistance",
            "Send portfolio briefings to Telegram",
            "Track unrealized P/L and dividend yield"
        ],
        "confidence": 0.92,
        "blast_radius": {"files": 4, "lines": 250},
        "outcome": {"status": "success", "score": 0.92},
        "env_fingerprint": {"platform": "linux", "arch": "x64"}
    }
    event = {
        "type": "EvolutionEvent",
        "intent": "optimize",
        "outcome": {"status": "success", "score": 0.92},
        "mutations_tried": 3,
        "total_cycles": 5
    }
    return gene, capsule, event

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()

    node_id, secret = load_creds()
    gene_data, capsule_data, event_data = example_bundle()
    assets = build_bundle(gene_data, capsule_data, event_data)

    print(f"Gene ID:    {gene_data['asset_id']}")
    print(f"Capsule ID: {capsule_data['asset_id']}")
    print(f"Event ID:   {event_data['asset_id']}")

    # Validate
    env = make_envelope(node_id, "validate", assets)
    print("\n=== VALIDATING ===")
    r = api_post("/a2a/validate", env, secret, args.max_retries)
    print(json.dumps(r, indent=2)[:1500])

    if r.get("payload", {}).get("valid") and not args.validate_only:
        print("\n=== PUBLISHING ===")
        pub_env = make_envelope(node_id, "publish", assets)
        r2 = api_post("/a2a/publish", pub_env, secret, args.max_retries)
        print(json.dumps(r2, indent=2)[:1500])
    elif args.validate_only:
        print("\n(validate-only mode, not publishing)")
    else:
        print("\n=== VALIDATION FAILED ===")
