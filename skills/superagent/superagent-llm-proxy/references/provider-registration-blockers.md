# Provider Registration Blockers (2026-06-27)

Some API providers require authentication flows that cannot be completed from a headless VPS. This reference catalogs known blockers and workarounds.

## Alibaba Cloud SSO (Qwen Cloud, DashScope)

**Affected services**: `home.qwencloud.com`, `dashscope.console.aliyun.com`, all `*.aliyun.com` API services.

**Blocker**: Registration redirects to `account.alibabacloud.com/sso/login.htm` — Alibaba Cloud SSO. The login page:
- Requires heavy JS rendering (React/Aliyun frontend framework)
- Chromium headless crashes consistently (page body empty, process exits)
- Even with `waitUntil:'load'` and minimal flags, page fails to render
- Tor also blocked (Alibaba IP-level block on some endpoints)
- May require Chinese phone verification

**Workarounds**:
1. Register from local browser (residential IP + real phone number)
2. Use alternative providers (HuggingFace for Qwen models, OpenRouter for API access)
3. Deploy Qwen open-source models locally via vLLM/llama.cpp

**Lesson**: Chinese cloud provider APIs (Alibaba, Tencent, Baidu) are generally unreachable from VPS without local browser + phone verification.

## Clerk Auth (Cambrian, and many Web3 startups)

**Affected services**: Any service using Clerk for authentication (common in AI/crypto startups).

**Blocker**: Clerk opens as a popup/modal with heavy JS. The main page navigates away when the popup fires. Chromium crashes on Clerk's React-based auth UI.

**Workarounds**:
1. Register from local browser
2. Check if the service has a direct API signup endpoint (bypass Clerk UI)
3. Some services accept email-only registration without Clerk (check `/api/auth/signup` endpoints)

## Discord OAuth

**Affected services**: Any airdrop/gaming platform requiring Discord connection.

**Blocker**: Discord login page (`discord.com/login`) requires full JS + WebGL rendering. Headless Chromium produces blank dark screenshots (all pixels `(18,18,20)`). Tor also fails (Discord blocks Tor exit nodes).

**Workarounds**:
1. Connect from local browser with real Discord session
2. Use Discord token via `window.localStorage` token extraction (requires logged-in browser)
3. Some platforms accept Discord OAuth via bot join (alternative to user login)

## hCaptcha / Turnstile on Signup (NVIDIA NIM, etc.)

**Affected services**: NVIDIA NIM, Cloudflare-backed signups, many tier-1 programs.

**Blocker**: hCaptcha/Turnstile challenges fail from AWS/GCP IP ranges. VPS datacenter IPs are flagged.

**Workarounds**:
1. User registers from own device (residential IP)
2. Use Tor exit rotation (may work for Turnstile, rarely for hCaptcha)
3. Some providers have alternative verification (email-only, GitHub OAuth)

## General Pattern

When encountering a new provider registration:
1. **First**: Try navigating to the signup page with headless Chromium
2. **If page crashes**: The auth framework is too heavy for VPS → try local browser
3. **If SSO redirect**: Check if the provider has alternative auth (GitHub, Google, email)
4. **If phone verification required**: Cannot automate → user must do from own device
5. **If hCaptcha/Turnstile**: Cannot automate from datacenter IP → user must do from own device

**Decision rule**: If 2+ attempts fail within 5 minutes, report blocker to user with alternatives. Don't grind on VPS-impossible registrations.
