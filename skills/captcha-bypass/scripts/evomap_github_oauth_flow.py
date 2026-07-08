#!/usr/bin/env python3
"""
EvoMap GitHub OAuth Flow via FlareSolverr
=========================================
Bypasses Cloudflare Turnstile on evomap.ai using FlareSolverr,
extracts GitHub OAuth URL, and optionally completes the callback.

Usage:
    python3 evomap_github_oauth_flow.py --extract-url    # Just get the GitHub OAuth URL
    python3 evomap_github_oauth_flow.py --complete CODE  # Complete OAuth with callback code
    python3 evomap_github_oauth_flow.py --check-account  # Check EvoMap account (after auth)

Requirements:
    - FlareSolverr running on localhost:8191
    - evomap.ai accessible via FlareSolverr (bypasses CF Turnstile)

Architecture:
    - EvoMap uses custom auth (not NextAuth.js)
    - GitHub OAuth: /api/auth/github → GitHub → /api/auth/github/callback?code=...
    - client_id: Ov23liQ8ewpLrpctOWRn
    - redirect_uri: https://evomap.ai/api/auth/github/callback
"""

import argparse
import json
import sys
import time
import requests

FS_URL = "http://localhost:8191/v1"
EVOMAP_GITHUB_OAUTH = "https://github.com/login/oauth/authorize?client_id=Ov23liQ8ewpLrpctOWRn&redirect_uri=https%3A%2F%2Fevomap.ai%2Fapi%2Fauth%2Fgithub%2Fcallback&scope=user%3Aemail"


def flaresolverr_session(session_name: str, cmd: str, **kwargs):
    """Execute a FlareSolverr command with session persistence."""
    payload = {"cmd": cmd, "session": session_name, "maxTimeout": 120000, **kwargs}
    r = requests.post(FS_URL, json=payload, timeout=180)
    return r.json()


def create_session(name: str):
    """Create a FlareSolverr session."""
    r = flaresolverr_session(name, "sessions.create")
    if r.get("status") != "ok":
        print(f"[ERROR] Failed to create session: {r}")
        sys.exit(1)
    print(f"[OK] Session '{name}' created")


def destroy_session(name: str):
    """Destroy a FlareSolverr session."""
    flaresolverr_session(name, "sessions.destroy")
    print(f"[OK] Session '{name}' destroyed")


def extract_github_oauth_url(session_name: str) -> str:
    """
    Use FlareSolverr to bypass CF Turnstile and extract the GitHub OAuth URL.
    
    Returns the full GitHub OAuth authorize URL that users should open in their browser.
    """
    create_session(session_name)
    
    # Step 1: Navigate to EvoMap login (bypasses Turnstile)
    print("[*] Navigating to evomap.ai/login via FlareSolverr...")
    r = flaresolverr_session(session_name, "request.get",
                              url="https://evomap.ai/login")
    if r.get("status") != "ok":
        print(f"[ERROR] Failed to access login page: {r}")
        destroy_session(session_name)
        sys.exit(1)
    
    cookies = r["solution"]["cookies"]
    print(f"[OK] Got {len(cookies)} cookies (cf_clearance={'cf_clearance' in [c['name'] for c in cookies]})")
    
    # Step 2: Navigate to GitHub OAuth endpoint
    print("[*] Navigating to /api/auth/github...")
    r = flaresolverr_session(session_name, "request.get",
                              url="https://evomap.ai/api/auth/github")
    
    if r.get("status") != "ok":
        print(f"[ERROR] Failed to access GitHub OAuth: {r}")
        destroy_session(session_name)
        sys.exit(1)
    
    github_url = r["solution"]["url"]
    print(f"[OK] GitHub OAuth URL: {github_url[:120]}...")
    
    # Save to file for reference
    output = {
        "github_oauth_url": github_url,
        "cookies": {c["name"]: c["value"] for c in cookies},
        "user_agent": r["solution"].get("userAgent", ""),
        "instructions": "Open this URL in your browser, login to GitHub, click Authorize, then paste the callback URL"
    }
    with open("/tmp/evomap_github_oauth.json", "w") as f:
        json.dump(output, f, indent=2)
    print("[OK] Saved to /tmp/evomap_github_oauth.json")
    
    destroy_session(session_name)
    return github_url


def complete_oauth(session_name: str, code: str) -> dict:
    """
    Complete the GitHub OAuth flow with the callback code.
    
    Args:
        code: The code from the GitHub callback URL (?code=XXXX)
    
    Returns:
        dict with session cookies and account info
    """
    create_session(session_name)
    
    # Navigate to callback URL to get session cookies
    callback_url = f"https://evomap.ai/api/auth/github/callback?code={code}"
    print(f"[*] Completing OAuth with code {code[:8]}...")
    
    r = flaresolverr_session(session_name, "request.get", url=callback_url)
    if r.get("status") != "ok":
        print(f"[ERROR] OAuth failed: {r}")
        destroy_session(session_name)
        sys.exit(1)
    
    final_url = r["solution"]["url"]
    cookies = {c["name"]: c["value"] for c in r["solution"]["cookies"]}
    
    print(f"[OK] Callback processed. Final URL: {final_url}")
    print(f"[OK] Cookies: {list(cookies.keys())}")
    
    # Check if we got EvoMap session cookies
    evomap_cookies = {k: v for k, v in cookies.items()
                      if "evomap" in k or k in ["cf_clearance", "g_state", "evomap_theme"]}
    
    if evomap_cookies:
        print(f"[OK] EvoMap session cookies obtained: {list(evomap_cookies.keys())}")
        
        # Save session
        with open("/tmp/evomap_session_cookies.json", "w") as f:
            json.dump(evomap_cookies, f)
        print("[OK] Session saved to /tmp/evomap_session_cookies.json")
    else:
        print("[!] Warning: No EvoMap-specific cookies found. User may need to complete login in browser.")
    
    destroy_session(session_name)
    return {"cookies": evomap_cookies, "final_url": final_url}


def check_account(session_name: str = None, cookies: dict = None) -> dict:
    """
    Check EvoMap account info using session cookies.
    
    Either provide an existing session_name or a cookies dict.
    """
    if cookies is None and session_name:
        create_session(session_name)
        r = flaresolverr_session(session_name, "request.get",
                                  url="https://evomap.ai/api/hub/account")
    elif cookies:
        s = requests.Session()
        for k, v in cookies.items():
            s.cookies.set(k, v, domain="evomap.ai")
        r = s.get("https://evomap.ai/api/hub/account", timeout=30)
        r = type("Response", (), {"json": lambda: r.json()})()
    else:
        print("[ERROR] Provide either session_name or cookies")
        return {}
    
    if isinstance(r, dict) and r.get("status") == "ok":
        body = r["solution"]["response"]
    else:
        try:
            body = r.json()
        except:
            body = {}
    
    if session_name:
        destroy_session(session_name)
    
    return body


def main():
    parser = argparse.ArgumentParser(description="EvoMap GitHub OAuth Flow via FlareSolverr")
    parser.add_argument("--session", default="evomap_flow", help="FlareSolverr session name")
    parser.add_argument("--extract-url", action="store_true", help="Extract GitHub OAuth URL")
    parser.add_argument("--complete", metavar="CODE", help="Complete OAuth with callback code")
    parser.add_argument("--check-account", action="store_true", help="Check EvoMap account")
    parser.add_argument("--cookies-file", default="/tmp/evomap_session_cookies.json",
                        help="Path to saved cookies file")
    
    args = parser.parse_args()
    
    if args.extract_url:
        url = extract_github_oauth_url(args.session)
        print(f"\n{'='*60}")
        print("OPEN THIS URL IN YOUR BROWSER:")
        print(f"{'='*60}")
        print(url)
        print(f"{'='*60}")
        print("After login, click Authorize, then paste the callback URL.")
    
    elif args.complete:
        result = complete_oauth(args.session, args.complete)
        if result["cookies"]:
            print("\n✅ OAuth complete! Session saved.")
            print("Run with --check-account to verify.")
        else:
            print("\n⚠️ OAuth processed but no session cookies obtained.")
    
    elif args.check_account:
        try:
            with open(args.cookies_file) as f:
                cookies = json.load(f)
            print("[*] Checking account with saved cookies...")
            info = check_account(cookies=cookies)
            print(json.dumps(info, indent=2))
        except FileNotFoundError:
            print(f"[ERROR] No cookies file at {args.cookies_file}")
            print("Run --extract-url first, then --complete CODE")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
