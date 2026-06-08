# Cloudflare WARP Setup — Free SOCKS5 Proxy for VPS

## What It Does
Routes all traffic through Cloudflare's network, exiting with a Cloudflare IP instead of your VPS provider's IP. **Unlimited bandwidth, free forever.**

## Why
Major platforms (Google, X/Twitter, Meta) block known datacenter ASNs (Amazon AWS, Google Cloud, Azure, etc.) at the IP reputation level — BEFORE any CAPTCHA. WARP exits with a Cloudflare IP (AS13335) that has much better reputation than any cloud provider.

## Is It Residential?
No — it's still a datacenter (Cloudflare) IP. But Cloudflare's ASN is far less blocklisted than AWS/GCP/Azure. It works for many sites that reject those providers.

## What Works with WARP
- ✅ X/Twitter API calls (requests/curl)
- ✅ Site pages that just need "not AWS" IP
- ✅ General web browsing from VPS
- ✅ Airdrop/signup form submission
- ⚠️ X/Twitter React SPA rendering (better than AWS, but not guaranteed)
- ❌ Google account creation (Google is extremely strict — needs real residential)

## Install Steps

```bash
# 1. Install WARP
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor \
  --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] \
  https://pkg.cloudflareclient.com/ bookworm main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
sudo apt-get update -qq
sudo apt-get install -y cloudflare-warp

# 2. Register + accept TOS (requires PTY)
script -qc 'warp-cli registration new' /dev/null <<< 'y'

# 3. Set mode to proxy (SOCKS5 on localhost:40000)
warp-cli mode proxy

# 4. Connect
warp-cli connect

# 5. Verify
warp-cli status  # Should say "Connected" and "Network: healthy"
curl -s --proxy socks5://127.0.0.1:40000 'https://api.ipify.org'  # Should return Cloudflare IP

# 6. Auto-start on boot
sudo tee /etc/systemd/system/warp-proxy.service << 'EOF'
[Unit]
Description=Cloudflare WARP SOCKS5 Proxy
After=network.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/warp-cli connect
ExecStop=/usr/bin/warp-cli disconnect
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable warp-proxy
```

## Hermes Integration

```bash
# Set browser proxy (requires gateway restart for browser tools)
hermes config set browser.proxy socks5://127.0.0.1:40000

# For CLI tools, use ALL_PROXY env var (immediate, no restart)
ALL_PROXY=socks5://127.0.0.1:40000 python3 x_tool.py whoami
```

## Proxy Config File
Save to `~/.hermes/proxy.conf`:
```env
WARP_SOCKS5=socks5://127.0.0.1:40000
WARP_EXIT_IP=<detected IP>
WARP_EXIT_ORG="Cloudflare, Inc."
```

## Pitfalls
- **TOS acceptance requires PTY** — use `script -qc` wrapper, not bare `warp-cli registration new`
- **`--accept-tos` flag does NOT exist** on `warp-cli registration new` (despite error message suggesting it)
- **`browser.proxy` config requires gateway restart** — doesn't take effect mid-session
- **Not residential** — won't bypass Google/X account creation (needs real residential proxy)
- **WARP daemon must stay running** — if `warp-cli status` shows Disconnected, reconnect with `warp-cli connect`
