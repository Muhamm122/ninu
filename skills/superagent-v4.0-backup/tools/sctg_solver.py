#!/usr/bin/env python3
"""
CUPANG CAPTCHA SOLVER — SCTG.xyz Integration
2captcha-compatible API — supports 35+ CAPTCHA types

Usage:
  python3 sctg_solver.py --type recaptcha_v2 --sitekey KEY --url URL
  python3 sctg_solver.py --type hcaptcha --sitekey KEY --url URL
  python3 sctg_solver.py --type turnstile --sitekey KEY --url URL
  python3 sctg_solver.py --type image --file captcha.png
  python3 sctg_solver.py --balance
"""

import os, sys, time, json, base64, argparse
import requests
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

API_KEY = os.getenv("SCTG_API_KEY", "")
ENDPOINT = os.getenv("SCTG_ENDPOINT", "https://sctg.xyz")

# ─── CORE API ───

def get_balance():
    """Check account balance (2captcha format)"""
    r = requests.get(f"{ENDPOINT}/res.php", params={"key": API_KEY, "action": "getbalance"}, timeout=10)
    return float(r.text)

def submit_task(params: dict) -> str:
    """Submit CAPTCHA solve request → returns request_id"""
    params["key"] = API_KEY
    r = requests.post(f"{ENDPOINT}/in.php", data=params, timeout=30)
    if not r.text.startswith("OK|"):
        raise Exception(f"Submit failed: {r.text}")
    return r.text.split("|")[1]

def get_result(request_id: str, timeout: int = 120) -> str:
    """Poll for result → returns CAPTCHA response token"""
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{ENDPOINT}/res.php", params={
            "key": API_KEY, "action": "get", "id": request_id
        }, timeout=10)
        if r.text == "CAPCHA_NOT_READY":
            time.sleep(3)
            continue
        if r.text.startswith("OK|"):
            return r.text.split("|", 1)[1]
        raise Exception(f"Solve failed: {r.text}")
    raise TimeoutError(f"Timeout after {timeout}s")

def solve(params: dict, timeout: int = 120) -> str:
    """Submit + poll → one-shot solve"""
    task_id = submit_task(params)
    return get_result(task_id, timeout)

# ─── CONVENIENCE FUNCTIONS ───

def solve_recaptcha_v2(sitekey: str, url: str, **kw) -> str:
    return solve({"method": "userrecaptcha", "googlekey": sitekey, "pageurl": url}, **kw)

def solve_recaptcha_v3(sitekey: str, url: str, action="verify", min_score=0.7, **kw) -> str:
    return solve({"method": "userrecaptcha", "version": "v3", "googlekey": sitekey,
                  "pageurl": url, "action": action, "min_score": min_score}, **kw)

def solve_hcaptcha(sitekey: str, url: str, **kw) -> str:
    return solve({"method": "hcaptcha", "sitekey": sitekey, "pageurl": url}, **kw)

def solve_turnstile(sitekey: str, url: str, **kw) -> str:
    return solve({"method": "turnstile", "sitekey": sitekey, "pageurl": url}, **kw)

def solve_image_base64(b64: str, **kw) -> str:
    return solve({"method": "base64", "body": b64}, **kw)

def solve_image_file(path: str, **kw) -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return solve_image_base64(b64, **kw)

# ─── CLI ───

PRICING = {
    "recaptcha_v2": "$0.07/1K", "recaptcha_v3": "$0.40/1K",
    "hcaptcha": "$0.015/1K", "turnstile": "$0.22/1K",
    "image": "$0.015/1K", "yandex": "$0.05/1K",
    "geetest": "$0.015/1K", "funcaptcha": "$0.10/1K",
    "slider": "$0.015/1K", "authkong": "$0.10/1K",
    "llm_ai": "$0.10/1K",
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SCTG CAPTCHA Solver")
    ap.add_argument("--type", choices=list(PRICING.keys()), help="CAPTCHA type")
    ap.add_argument("--sitekey", help="Site key")
    ap.add_argument("--url", help="Page URL")
    ap.add_argument("--file", help="Image file path")
    ap.add_argument("--balance", action="store_true", help="Check balance")
    args = ap.parse_args()

    if not API_KEY:
        print("❌ SCTG_API_KEY not set. Add to ~/.hermes/.env")
        sys.exit(1)

    if args.balance:
        bal = get_balance()
        print(f"💰 Balance: ${bal:.4f}")
        sys.exit(0)

    if not args.type:
        ap.print_help()
        print(f"\n📊 Pricing:")
        for t, p in PRICING.items():
            print(f"   {t}: {p}")
        sys.exit(0)

    t0 = time.time()
    print(f"🔄 Solving {args.type}...")

    try:
        if args.type == "recaptcha_v2":
            result = solve_recaptcha_v2(args.sitekey, args.url)
        elif args.type == "recaptcha_v3":
            result = solve_recaptcha_v3(args.sitekey, args.url)
        elif args.type == "hcaptcha":
            result = solve_hcaptcha(args.sitekey, args.url)
        elif args.type == "turnstile":
            result = solve_turnstile(args.sitekey, args.url)
        elif args.type == "image":
            result = solve_image_file(args.file)
        else:
            print(f"❌ Type '{args.type}' not yet implemented in CLI")
            sys.exit(1)

        elapsed = time.time() - t0
        print(f"✅ Solved in {elapsed:.1f}s")
        print(f"📌 Token: {result[:80]}..." if len(result) > 80 else f"📌 Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
