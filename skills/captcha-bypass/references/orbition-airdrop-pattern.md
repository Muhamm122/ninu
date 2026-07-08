# Orbition Airdrop — API Structure & Auth Pattern (Verified 2026-06-25)

## Overview
- **Frontend**: https://airdrop.orbition.network (React SPA, Next.js)
- **API**: https://api-airdrop.orbition.network (separate subdomain)
- **Auth**: Google OAuth + WalletConnect (Wagmi) + X OAuth
- **Token storage**: `localStorage.setItem("tokens", ...)` — JSON with access_token, refresh_token, expires_at
- **Referral code**: `8480609127`

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/quests` | GET | ❌ | List all quests (public) |
| `/api/quests/verify` | POST | ✅ | Complete a quest |
| `/api/me` | GET | ✅ | User profile + total rewards |
| `/api/wallet/link` | POST | ✅ | Link wallet address |
| `/api/mining/start` | POST | ✅ | Start AI mining |
| `/api/mining/claim` | POST | ✅ | Claim mining rewards |
| `/api/referrals/stats` | GET | ✅ | Referral statistics |
| `/api/referrals/top` | GET | ❌ | Top 20 referrers (public) |
| `/api/auth/google/callback` | POST | ❌ | Google OAuth callback |
| `/api/auth/x/callback` | POST | ❌ | X OAuth callback |
| `/api/auth/refresh` | POST | ❌ | Refresh token |
| `/api/time` | GET | ❌ | Server timestamp |

## Auth Flow
1. User clicks "Sign In" → Google OAuth popup
2. Google returns auth code → POST to `/api/auth/google/callback`
3. Backend returns tokens → stored in localStorage
4. User connects wallet via WalletConnect → POST to `/api/wallet/link`
5. User connects X via OAuth → POST to `/api/auth/x/callback`

## Why It Can't Be Bypassed
- **Google OAuth is compliant** — requires real browser fingerprint + human interaction (password/2FA)
- **CloakBrowser reaches password page** but cannot fill password (security policy)
- **Residential proxy (InstantProxies/T-Mobile) causes 30s timeout** on Google pages
- **Token required for all write operations** — no way to complete quests without auth
- **Public read endpoints** (quests, leaderboard) don't need auth but are read-only

## Quests Available
| # | Task | Reward | Auto? |
|---|------|--------|-------|
| 1 | Subscribe Newsletter | 500 OBN | ❌ Need email |
| 2 | Follow X | 500 OBN | ❌ Need X OAuth |
| 3 | Join Telegram Community | 500 OBN | ❌ Need TG join |
| 4 | Join Telegram Channel | 500 OBN | ❌ Need TG join |
| 5 | Like & Retweet (post 1) | 300 OBN | ❌ Need X OAuth |
| 6 | Like & Retweet (post 2) | 500 OBN | ❌ Need X OAuth |
| 7 | Like & Retweet (post 3) | 300 OBN | ❌ Need X OAuth |

**Total social rewards: ~2,800 OBN**
**Mining: variable (0.01 OBN/sec, 24h cooldown)**

## Self-Service Script
See `~/.hermes/scripts/orbition_auto.py` — user provides token from localStorage, script handles:
- Account status check
- Quest completion (auto where possible)
- Mining start + claim
- Referral stats

## Pattern Classification
This is a **"proper auth"** airdrop — Google OAuth + WalletConnect + X OAuth. Unlike Privy-based airdrops (which can be bypassed via email OTP), this requires real social account connections. The only automation possible is post-auth (after user logs in manually and provides token).

## Discovery Notes
- JS bundle at `/assets/index-*.js` contains all API endpoints
- API domain discovered by grepping JS for `https://` patterns → found `api-airdrop.orbition.network`
- Token format: `{"access_token":"eyJ...","refresh_token":"...","expires_at":...}`
- Referral code stored in localStorage as `referrer_code`
- **General pattern**: Many airdrops use separate API subdomain (api.airdrop.domain.com) — always grep JS bundles for `https://` to find it