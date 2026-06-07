# Airdrop Research Pattern

Reusable workflow for investigating and participating in Web3 airdrops.

## Step 1: Page Recon

1. Navigate to the airdrop page in browser.
2. Dismiss onboarding dialogs (welcome modal, cookie banners).
3. Extract key info from page text: pool size, reward per wallet, registered count, max slots, deadline, referral code, wallet address for "grow the pool".

## Step 2: API Discovery

Use browser console to find API endpoints:
```javascript
const entries = performance.getEntriesByType('resource');
const apiCalls = entries.filter(e => e.name.includes('api') || e.name.includes('airdrop') || e.name.includes('register')).map(e => e.name);
JSON.stringify(apiCalls);
```

Common endpoint patterns:
- `GET /api/airdrop/stats` — pool balance, registration count, slots, wallet address, mint, deadline
- `GET /api/airdrop/status` — authenticated status, registration status
- `POST /api/airdrop/register` — register for airdrop (requires auth session)
- `GET /api/auth/me` — check if logged in

## Step 3: API Inspection

```bash
# Stats (usually public, no auth)
curl -s 'https://DOMAIN/api/airdrop/stats' | python3 -m json.tool

# Status (tells if current session is registered)
curl -s 'https://DOMAIN/api/airdrop/status' | python3 -m json.tool

# Try register without auth (reveals auth requirement message)
curl -s -X POST 'https://DOMAIN/api/airdrop/register' -H 'Content-Type: application/json' -d '{}'
```

## Step 4: Wallet Preparation

Generate wallets for the target chain. See SKILL.md for chain-specific instructions.

For Solana:
```python
from solders.keypair import Keypair
import base58, json
wallets = []
for i in range(N):
    kp = Keypair()
    wallets.append({
        'id': i + 1,
        'public_key': str(kp.pubkey()),
        'secret_base58': base58.b58encode(bytes(kp)).decode()
    })
```

For EVM:
```python
from eth_account import Account
Account.enable_unaudited_hdwallet_features()
acct, mnemonic = Account.create_with_mnemonic(num_words=24)
```

## Step 5: Anti-Sybil Analysis

Before multi-wallet registration, analyze the anti-sybil rules:

| Rule Type | Common Implementation | Impact on Multi-Wallet |
|-----------|----------------------|----------------------|
| **1 per identity** | X handle, Telegram, email, Discord | Need N separate accounts |
| **1 per wallet** | Solana/EVM address check | Need N wallets (easy) |
| **Duplicate rejection** | At signup AND distribution | Both must pass |
| **KYC** | ID verification / OTP | Very hard to multi-wallet |
| **On-chain activity** | Must have tx history / balance | Need to fund each wallet |
| **Token snapshot** | Must hold token at snapshot block | Buy token per wallet |

**Decision framework**:
- If anti-sybil is identity-only (no KYC): multi-wallet is possible but each needs a unique identity account.
- If anti-sybil is wallet-only: easy — just generate N wallets.
- If both: need N identities × N wallets, and must avoid correlation patterns.
- If KYC required: single-wallet only, not worth the effort/ethics.

## Step 6: Pool Status Decision

```
remainingSlots > 0  →  Register immediately
remainingSlots == 0 AND pool can grow  →  Send tokens to grow pool wallet → creates new slots
remainingSlots == 0 AND pool fixed  →  Check for waitlist, follow socials for pool expansion announcements
registration closed  →  Skip, look for next airdrop
```

## Step 7: Registration Pattern

Most airdrops follow this flow:
1. **Sign in** to the platform (X OAuth, wallet connect, email+OTP)
2. **Connect wallet** (Solana: sign message, no gas; EVM: sign EIP-712 message)
3. **Register** (POST to /api/airdrop/register with session cookie)
4. **Optional social tasks** (follow, like, retweet, tag friends)
5. **Wait for distribution** (usually after deadline/closes)

## Case Study: pimp.zone (2026-06)

- **Token**: $PIMPZONE (mint: `DBF1Qcs9qpYFnrpJxmcFt2rNtSAE1eNHa6PrJEi9AKaU`)
- **Reward**: 5,000 per wallet
- **Pool**: 15,000,000 (3,000 slots)
- **Anti-sybil**: 1 per X handle, 1 per wallet, duplicate rejection at signup AND distribution
- **Status**: Full (3,000/3,000), but "grow the pool" available — send $PIMPZONE to `DBvW3yVzUDY6aSWANKNPHmrQysZzHDNVa39buAosCBgq` to create new registration slots
- **Close**: 2026-06-17T23:59:59Z
- **Auth**: X, Telegram, or email+password
- **Referral**: `?ref=CODE` in URL
