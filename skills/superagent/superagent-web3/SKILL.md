---
name: superagent-web3
description: "Web3 ops, on-chain operations, mass farming, airdrop automation."
---

## Operator Profile

On-chain operator. Builds reliable scripts that interact with EVM/non-EVM chains. Bias toward simulation before broadcast, gas optimization, RPC redundancy, nonce safety.

---

## Stack Defaults

```
EVM JS:           ethers v6 (preferred for stability) OR viem (preferred for type safety / perf)
EVM Python:       web3.py v7+
Solana:           @solana/web3.js + @solana/spl-token
Wallet gen:       ethers.Wallet.createRandom() / bip39 + ethers HDNode
Storage:          .env for keys, encrypted JSON for batch wallets
Indexing/RPC:     Alchemy, Infura, Ankr, public RPCs (with fallback array)
```

---

## RPC Fallback Pattern (anti-fragile)

```javascript
const { JsonRpcProvider, FallbackProvider } = require('ethers');

const RPCS = {
  ethereum: [
    'https://eth.llamarpc.com',
    'https://rpc.ankr.com/eth',
    `https://mainnet.infura.io/v3/${process.env.INFURA_KEY}`,
  ],
  base: [
    'https://mainnet.base.org',
    'https://base.llamarpc.com',
    'https://base.publicnode.com',
  ],
  bsc: [
    'https://bsc-dataseed.binance.org',
    'https://bsc-dataseed1.defibit.io',
    'https://rpc.ankr.com/bsc',
  ],
  polygon: [
    'https://polygon-rpc.com',
    'https://rpc.ankr.com/polygon',
  ],
};

function getProvider(chain) {
  const providers = RPCS[chain].map((url, i) => ({
    provider: new JsonRpcProvider(url),
    priority: i + 1,
    weight: 1,
    stallTimeout: 1500,
  }));
  return new FallbackProvider(providers, { quorum: 1 });
}
```

---

## Wallet Operations

### Generate fresh wallet (random)

```javascript
const { Wallet } = require('ethers');
const w = Wallet.createRandom();
console.log({ address: w.address, privateKey: w.privateKey, mnemonic: w.mnemonic.phrase });
```

### Generate from mnemonic (BIP39, deterministic — for batch ops)

```javascript
const { Mnemonic, HDNodeWallet } = require('ethers');
const phrase = 'word1 word2 ... word12';
const mnem = Mnemonic.fromPhrase(phrase);

// Derive multiple wallets from same mnemonic
for (let i = 0; i < 300; i++) {
  const w = HDNodeWallet.fromMnemonic(mnem, `m/44'/60'/0'/0/${i}`);
  console.log(i, w.address);
}
```

### Wallet pool with encrypted storage

```javascript
const fs = require('fs');
const { Wallet } = require('ethers');

// Save batch encrypted
async function saveWallets(wallets, password, path = 'wallets.enc.json') {
  const encrypted = await Promise.all(wallets.map(w => w.encrypt(password)));
  fs.writeFileSync(path, JSON.stringify(encrypted, null, 2));
}

// Load batch
async function loadWallets(password, provider, path = 'wallets.enc.json') {
  const blobs = JSON.parse(fs.readFileSync(path, 'utf-8'));
  return Promise.all(blobs.map(b => Wallet.fromEncryptedJson(b, password).then(w => w.connect(provider))));
}
```

---

## Transaction Pattern (simulate → estimate → send → wait)

```javascript
const { Contract, parseEther, parseUnits } = require('ethers');

async function sendTx({ wallet, to, value = 0n, data = '0x' }) {
  const tx = {
    to,
    value,
    data,
    nonce: await wallet.getNonce('pending'),     // 'pending' prevents nonce gaps
  };

  // 1. Simulate (catches reverts before paying gas)
  try {
    await wallet.call(tx);
  } catch (e) {
    throw new Error(`Simulation reverted: ${e.shortMessage || e.message}`);
  }

  // 2. Estimate gas with 20% buffer
  const gasEst = await wallet.estimateGas(tx);
  tx.gasLimit = (gasEst * 120n) / 100n;

  // 3. Fee data (EIP-1559)
  const fee = await wallet.provider.getFeeData();
  tx.maxFeePerGas = fee.maxFeePerGas;
  tx.maxPriorityFeePerGas = fee.maxPriorityFeePerGas;

  // 4. Broadcast
  const resp = await wallet.sendTransaction(tx);
  console.log('Sent:', resp.hash);

  // 5. Wait for confirmation
  const rcpt = await resp.wait(1);   // 1 confirmation
  if (rcpt.status === 0) throw new Error(`Tx reverted: ${resp.hash}`);
  return rcpt;
}
```

---

## Contract Interaction (ethers v6)

```javascript
const { Contract } = require('ethers');

const ERC20_ABI = [
  'function balanceOf(address) view returns (uint256)',
  'function transfer(address,uint256) returns (bool)',
  'function decimals() view returns (uint8)',
  'function symbol() view returns (string)',
  'event Transfer(address indexed from, address indexed to, uint256 value)',
];

async function checkBalance(provider, token, holder) {
  const c = new Contract(token, ERC20_ABI, provider);
  const [bal, dec, sym] = await Promise.all([c.balanceOf(holder), c.decimals(), c.symbol()]);
  return { raw: bal, formatted: Number(bal) / 10 ** Number(dec), symbol: sym };
}

async function transferToken(wallet, token, to, amount) {
  const c = new Contract(token, ERC20_ABI, wallet);
  const dec = await c.decimals();
  const tx = await c.transfer(to, parseUnits(String(amount), dec));
  return tx.wait();
}
```

---

## Nonce Management (avoid stuck/replaced tx)

```javascript
class NonceManager {
  constructor(wallet) { this.wallet = wallet; this.cache = null; }

  async next() {
    if (this.cache === null) {
      this.cache = await this.wallet.getNonce('pending');
    }
    const n = this.cache++;
    return n;
  }

  async reset() {
    this.cache = await this.wallet.getNonce('pending');
  }
}

// Use across multiple parallel sends
const nm = new NonceManager(wallet);
const txs = await Promise.all(targets.map(async t => {
  return wallet.sendTransaction({ to: t, value: parseEther('0.01'), nonce: await nm.next() });
}));
```

---

## Gas Optimization

```javascript
async function getGasStrategy(provider, urgency = 'standard') {
  const fee = await provider.getFeeData();
  const mult = { slow: 0.85, standard: 1.0, fast: 1.25, asap: 1.5 }[urgency] || 1.0;
  return {
    maxFeePerGas: BigInt(Math.floor(Number(fee.maxFeePerGas) * mult)),
    maxPriorityFeePerGas: BigInt(Math.floor(Number(fee.maxPriorityFeePerGas) * mult)),
  };
}
```

---

## Airdrop Eligibility Checker (O(1) lookup)

```javascript
const fs = require('fs');

// Build set once from snapshot
const eligible = new Set(
  JSON.parse(fs.readFileSync('snapshot.json'))
    .map(a => a.toLowerCase())
);
console.log(`Loaded ${eligible.size.toLocaleString()} eligible addresses`);

function isEligible(address) {
  return eligible.has(address.toLowerCase());
}

// For Telegram bot integration:
bot.onText(/^\/check (.+)/, (msg, match) => {
  const addr = match[1].trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(addr)) {
    return bot.sendMessage(msg.chat.id, '❌ Invalid address format.');
  }
  const ok = isEligible(addr);
  bot.sendMessage(msg.chat.id, ok ? `✅ Eligible: ${addr}` : `❌ Not in snapshot: ${addr}`);
});
```

For 1M+ addresses: switch to SQLite with index on `address` column.

---

## Mass Mining/Farming Pattern (with rate limits + concurrency cap)

```javascript
const pLimit = require('p-limit').default;
const limit = pLimit(5);   // max 5 concurrent

const wallets = await loadWallets('passphrase', provider);

const results = await Promise.allSettled(
  wallets.map(w => limit(async () => {
    try {
      const tx = await runQuest(w);   // operator-specific quest function
      return { addr: w.address, hash: tx.hash, ok: true };
    } catch (e) {
      return { addr: w.address, error: e.message, ok: false };
    }
  }))
);

const ok = results.filter(r => r.value?.ok).length;
console.log(`Done: ${ok}/${wallets.length} succeeded`);
```

---

## Token Snapshot (read holders from chain)

```javascript
const { Contract } = require('ethers');
const ERC20_ABI = ['event Transfer(address indexed from, address indexed to, uint256 value)'];

async function snapshotHolders(provider, token, fromBlock, toBlock) {
  const c = new Contract(token, ERC20_ABI, provider);
  const events = await c.queryFilter('Transfer', fromBlock, toBlock);

  const holders = new Map();
  for (const ev of events) {
    const { from, to, value } = ev.args;
    holders.set(from, (holders.get(from) || 0n) - value);
    holders.set(to,   (holders.get(to)   || 0n) + value);
  }
  return [...holders.entries()].filter(([_, v]) => v > 0n);
}
```

Note: for chains with millions of events, chunk by block range (e.g., 10k blocks/chunk) to avoid RPC limits.

---

## Solana Quick Reference

### JavaScript (@solana/web3.js)

```javascript
const { Connection, Keypair, LAMPORTS_PER_SOL, PublicKey, SystemProgram, Transaction } = require('@solana/web3.js');
const bs58 = require('bs58');

const connection = new Connection('https://api.mainnet-beta.solana.com', 'confirmed');
const payer = Keypair.fromSecretKey(bs58.decode(process.env.SOL_PRIVATE_KEY));

const balance = await connection.getBalance(payer.publicKey);
console.log('SOL:', balance / LAMPORTS_PER_SOL);

const tx = new Transaction().add(
  SystemProgram.transfer({
    fromPubkey: payer.publicKey,
    toPubkey: new PublicKey(recipient),
    lamports: 0.01 * LAMPORTS_PER_SOL,
  })
);
const sig = await connection.sendTransaction(tx, [payer]);
console.log('Sig:', sig);
```

### Python (solders) — Wallet Generation

Install: `pip install solders base58`

```python
from solders.keypair import Keypair
import base58, json

# Generate single wallet
kp = Keypair()
pubkey = str(kp.pubkey())        # ⚠️ METHOD CALL, not property! .pubkey() not .pubkey
secret_bytes = bytes(kp)         # 64-byte secret (NOT kp.secret_key — doesn't exist)
secret_b58 = base58.b58encode(secret_bytes).decode()

# Batch generate
wallets = []
for i in range(N):
    kp = Keypair()
    wallets.append({
        'id': i + 1,
        'public_key': str(kp.pubkey()),
        'secret_base58': base58.b58encode(bytes(kp)).decode()
    })

with open('sol-wallets.json', 'w') as f:
    json.dump(wallets, f, indent=2)
```

**⚠️ solders API Pitfalls (Python)**
- `.pubkey` is a **method**, not a property → must call `kp.pubkey()` with parens. `str(kp.pubkey)` returns `<built-in method ...>` not the address!
- `.secret_key` does **NOT exist** on Keypair in solders ≥0.x. Use `bytes(kp)` for the 64-byte secret. Attempting `kp.secret_key` raises `AttributeError`.
- `.secret` exists but returns a different format — `bytes(kp)` is the canonical 64-byte representation compatible with `Keypair.from_bytes()`.
- For JSON storage: encode secret as base58 string via `base58.b58encode(bytes(kp)).decode()`.
- Restore from base58: `kp = Keypair.from_bytes(base58.b58decode(secret_b58))`.
- **Import check**: `from solders.keypair import Keypair` — if this fails, install: `pip install solders base58`.
- **from_seed vs from_bytes**: `Keypair.from_seed(bytes)` takes a 32-byte seed (derives full keypair). `Keypair.from_bytes(bytes)` takes 64-byte full secret. JSON files storing 32-byte arrays need `from_seed()`; 64-byte arrays need `from_bytes()`. Attempting `from_bytes()` on 32 bytes raises `expected a sequence of length 64 (got 32)`.

### Solana Wallet Auth (Nonce-Based Sign-In)

Many Solana dApps (pimp.zone, etc.) use nonce-based signature auth:

```
1. POST /api/auth/nonce  {wallet: base58_address}  → {message, nonce, expiresAt}
2. Signature = sign_message( TextEncoder.encode(message) )   ← sign the FULL message string
3. POST /api/auth/login {wallet, signature: base58(sig_bytes), nonce}
```

**Critical encoding**: The signature sent to `/api/auth/login` must be **base58-encoded** (NOT base64, NOT hex). Use `base58.b58encode(sig.to_bytes()).decode()` in Python.

```python
import base58, subprocess, json
from solders.keypair import Keypair

def solana_login(domain: str, wallet_pubkey_b58: str, kp: Keypair, proxy: str = None) -> dict:
    """Full nonce-based auth for Solana dApps. Returns login response."""
    cmd = ['curl', '-s', '-X', 'POST']
    if proxy:
        cmd.extend(['--socks5', proxy])
    cmd += [f'https://{domain}/api/auth/nonce', '-H', 'Content-Type: application/json',
            '-d', json.dumps({'wallet': wallet_pubkey_b58})]
    
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
    message, nonce = data['message'], data['nonce']
    
    # Sign the encoded message
    sig = kp.sign_message(message.encode('utf-8'))
    sig_b58 = base58.b58encode(sig.to_bytes()).decode()
    
    # Login
    cmd2 = ['curl', '-s', '-X', 'POST']
    if proxy:
        cmd2.extend(['--socks5', proxy])
    cmd2 += [f'https://{domain}/api/auth/login', '-H', 'Content-Type: application/json',
             '-d', json.dumps({'wallet': wallet_pubkey_b58, 'signature': sig_b58, 'nonce': nonce})]
    
    return json.loads(subprocess.run(cmd2, capture_output=True, text=True).stdout)
```

**Pitfalls**:
- Sending base64 or hex signature → `{"error": "Invalid signature"}`. Always base58.
- Signing the nonce only (not full message) → `{"error": "Invalid signature"}`. Sign the `message` field from nonce response.
- Using `Keypair.from_bytes(secret_key_array)` when JSON has 32 bytes → `expected sequence of length 64`. Use `from_seed()` for 32-byte seeds.
- Signature valid but `{"error": "Signups from your region aren't supported"}` → IP-based geolocation block at middleware level. Header spoofing (`X-Forwarded-For`, `CF-IPCountry`) is ignored. Need residential proxy from allowed region.

### Region-Blocking Bypass

When an API responds with region-blocked error despite valid credentials:
1. **Header spoofing does NOT work** — servers use actual connection IP, not `X-Forwarded-For`
2. **WARP proxy** always exits from nearest region (e.g., SG for AWS SG VPS) — may also be blocked
3. **Only fix**: residential/business proxy with IP from allowed region (US/EU typically)
4. Check exit IP: `curl -s --socks5 127.0.0.1:40000 https://api.ipify.org?format=json`
5. Check exit country: `curl -s --socks5 127.0.0.1:40000 https://ipinfo.io/country`

### Next.js Auth Code Extraction

When auth flow is hidden in minified Next.js bundles, extract the logic by:

1. Get all script chunks from page HTML: `re.findall(r'src="(/_next/static/chunks/[^"]+\.js)"', html)`
2. Download each chunk and search for auth-related strings: `re.findall(r'["\x60](/api/(?:auth|login|signup|register|wallet|user)[^"\x60]*)["\x60]', code)`
3. Find the chunk containing `/api/auth/login` and extract surrounding context (±500 chars) to understand the full auth flow
4. Look for encoding functions (e.g., `tR.default.encode`) — trace back to identify if it's base58, base64, or hex

### Browser Wallet Mock Injection (for headless testing)

When testing dApp auth flows in headless browser without real wallet extension:

```javascript
// Inject persistent mock wallet via Object.defineProperty
const fakePubkey = { toBase58: () => 'WALLET_ADDRESS' };
const fakeWallet = {
  isPhantom: true, isConnected: true, publicKey: fakePubkey,
  connect: async function(opts) { return { publicKey: fakePubkey }; },
  signMessage: async function(message) {
    const msgStr = new TextDecoder().decode(message);
    console.log('[MOCK] signMessage:', msgStr);
    window.__lastSignMessage = msgStr;
    return new Uint8Array(64).fill(42);  // dummy sig
  },
  on: function() {}, off: function() {}
};
Object.defineProperty(window, 'solana', { value: fakeWallet, writable: true, configurable: true });
Object.defineProperty(window, 'phantom', { value: { solana: fakeWallet }, writable: true, configurable: true });
```

**Note**: React re-renders may reset `window.solana`. Use `Object.defineProperty` (not direct assignment) for persistence. Also inject fetch interceptor to capture auth requests:

```javascript
window.__origFetch = window.fetch;
window.__capturedReqs = [];
window.fetch = async function(...args) {
  const url = typeof args[0] === 'string' ? args[0] : args[0]?.url;
  if (url && url.includes('/api/')) {
    window.__capturedReqs.push({url, method: args[1]?.method, body: args[1]?.body?.toString?.()});
  }
  return window.__origFetch.apply(this, args);
};
```

### Solana JSON-RPC (curl / requests — no SDK needed)

```bash
# Check SOL balance
curl -s https://api.mainnet-beta.solana.com -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getBalance","params":["WALLET_PUBKEY"]}' | python3 -m json.tool

# Check SPL token account
curl -s https://api.mainnet-beta.solana.com -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getTokenAccountsByOwner","params":["WALLET_PUBKEY",{"mint":"TOKEN_MINT"},{"encoding":"jsonParsed"}]}' | python3 -m json.tool

# Request airdrop (devnet/testnet only, 1 SOL max)
curl -s https://api.devnet.solana.com -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"requestAirdrop","params":["WALLET_PUBKEY",1000000000]}'
```

---

## Airdrop Research

See `references/airdrop-research-pattern.md` for the full investigative workflow: API discovery via browser performance entries, stats/status inspection, anti-sybil analysis, pool status decision framework, registration flow patterns, **auto-OTP via IMAP polling** (Step 7c), browser form → curl fallback (Step 7b), **Telegram bot airdrop automation** (Step 7d), and **X/Twitter API action automation** (Step 7e). Includes pimp.zone, Tplus, Vinci World, and DOR case studies.

### Telegram Bot Airdrop Pattern (Step 7d)

Most Telegram airdrop bots follow a predictable flow that can be fully automated with Telethon:

1. **Start bot**: Send `/start ref_CODE` via `client.send_message(bot_entity, '/start ref_XXXX')`
2. **Solve math captcha**: Parse `A + B = ?` from bot response, send answer
3. **Click task buttons**: Iterate `msg.buttons` rows, click each to verify task
4. **Submit profile links**: Bot asks for Twitter/Discord profile URLs → send as text
5. **Submit wallet**: Bot asks for EVM/Solana address → send from wallets.enc
6. **Complete**: Look for "Congratulations" or similar confirmation

Key Telethon patterns:
- Get bot entity: `entity = await client.get_entity('BotUsername')`
- Click inline button: `await msg.buttons[row_index][col_index].click()`
- Read response after click: `await asyncio.sleep(3-5)` then `client.get_messages(entity, limit=2)`
- Join channels/groups: `from telethon.tl.functions.channels import JoinChannelRequest` then `await client(JoinChannelRequest(await client.get_input_entity('channel_name')))`
- Join via invite link: `from telethon.tl.functions.messages import ImportChatInviteRequest` then `await client(ImportChatInviteRequest('invite_hash'))`

⚠️ **Pitfall**: Telegram bot buttons are indexed as `msg.buttons[row][col]`. When clicking, use `btn.click()` on the button object directly — don't use `msg.click(i, j)` which can have row/col reversed depending on Telethon version. Always click the button object from the 2D array.
⚠️ **Pitfall**: After clicking a button, the bot may take 3-5 seconds to respond. Always `await asyncio.sleep(3)` before reading new messages.
⚠️ **Pitfall**: "Skip this task" buttons exist for optional tasks. Use them when the task platform isn't accessible (e.g., Discord without an account).
⚠️ **Pitfall**: Telegram session files can be stale. Always check multiple session paths and call `await client.is_user_authorized()` — don't assume a `.session` file is valid. Known paths: `~/.hermes/tg_user.session` (primary), `~/.hermes/tg-user-session.session`, `~/adib_session.session` (often stale).

### Website WL Form with Toggle-Done Checkboxes (Step 7f)

Some airdrop sites (Dumbois, etc.) use **self-reported task completion**: fill X username + wallet, toggle `.task-check` checkboxes to mark tasks done, progress bar hits 100%, submit `POST /api/apply`. The checkboxes are NOT verified — but always do the social tasks for real anyway (via `airdrop_follow`, `like`, `retweet`) to survive post-submission audits.

```javascript
// Toggle all task checkboxes, then intercept submit payload
document.querySelectorAll('.task-check').forEach(c => c.click());
```

Full pattern + Dumbois case study in `references/airdrop-research-pattern.md` Step 7f.

### X/Twitter API Automation for Airdrops (Step 7e)

Use x-actions (or direct GraphQL API) to complete Twitter airdrop tasks (follow, like, retweet, post) without browser:

1. **Lookup user**: `user_lookup('handle')` → returns rest_id, followers count
2. **Follow**: `airdrop_follow('handle')` or `follow(user_id)` → REST API `POST /1.1/friendships/create.json`
3. **Like**: `like(tweet_id)` → GraphQL `FavoriteTweet` mutation
4. **Retweet**: `retweet(tweet_id)` → GraphQL `CreateRetweet` mutation (requires fresh QID + operation_name in URL)
5. **Post**: `post('text')` → GraphQL `CreateTweet` mutation
6. **Full garapan**: `garap_full('handle', tweet_id)` → follow + like + retweet + quote in sequence with random delays

⚠️ **QID Discovery**: GraphQL queryIds change with X deployments. Extract fresh ones by:
```python
scripts = re.findall(r'src="(https://abs\.twimg\.com/responsive-web/client-web[^"]+\.js)"', requests.get('https://x.com').text)
# Then search each JS bundle for: queryId:"XXXX" ... operationName:"OperationName"
```
⚠️ **v1.1 API is dead (2026-06)**: `api.x.com/1.1/statuses/user_timeline.json` returns 404 (not 401). Do NOT use any v1.1 endpoints. Use GraphQL exclusively.
⚠️ **QID HTML discovery blocked**: `requests.get('https://x.com')` returns 401. JS bundle URLs only accessible via browser rendering. Use cached QIDs or Playwright+CDP to intercept.
Generic QID `D1nwFlsu_qHsX92YzoRaaA` applies to many operations but is NOT the real per-operation QID and returns 405 on write mutations. Always use the specific QID paired with the operationName.

⚠️ **operation_name in URL**: X GraphQL write endpoints require the operation name in the URL path: `https://x.com/i/api/graphql/{QID}/{OperationName}`. Without it, the API returns 405. Always pass `operation_name=` to `_api_post()`.

⚠️ **FEATURES dict**: Bloated features dicts can cause 405. Start minimal and add only what's needed. For CreateTweet, include: `rweb_tipjar_consumption_enabled`, `responsive_web_graphql_exclude_directive_enabled`, `responsive_web_graphql_timeline_navigation_enabled`, `creator_subscriptions_tweet_preview_api_enabled`, `responsive_web_edit_tweet_api_enabled`, `view_counts_everywhere_api_enabled`.

⚠️ **Bearer token**: Auto-extract from X JS bundles or use fallback `AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA`. Store at `~/.hermes/x-bearer.txt`.

## On-Chain Common Patterns

### Approve + Spend (DEX swap, staking, etc.)

```javascript
const erc20 = new Contract(token, ERC20_ABI, wallet);
const router = new Contract(routerAddress, ROUTER_ABI, wallet);

// Check current allowance
const allowance = await erc20.allowance(wallet.address, routerAddress);
if (allowance < amount) {
  console.log('Approving...');
  const tx = await erc20.approve(routerAddress, ethers.MaxUint256);
  await tx.wait();
}
// Now safe to call router
await router.swap(...);
```

### Multicall (batch reads in one RPC call)

```javascript
const { Multicall } = require('ethereum-multicall');
const mc = new Multicall({ ethersProvider: provider, tryAggregate: true });
const calls = addresses.map(a => ({
  reference: a,
  contractAddress: token,
  abi: ERC20_ABI,
  calls: [{ methodName: 'balanceOf', methodParameters: [a] }],
}));
const { results } = await mc.call(calls);
```

---

## Wallet Generation (Python — eth_account)

When `ethers` JS is not available, use Python `eth_account` (install: `pip install eth_account`).

```python
from eth_account import Account
Account.enable_unaudited_hdwallet_features()

# Generate 24-word mnemonic wallet
acct, mnemonic = Account.create_with_mnemonic(num_words=24, passphrase="")

result = {
    "chain": "EVM",
    "address": acct.address,
    "private_key": "0x" + acct.key.hex(),
    "mnemonic": mnemonic,
    "derivation_path": "m/44'/60'/0'/0/0",
}
```

Same address works on all EVM chains: Ethereum, BSC, Base, Arbitrum, Optimism, Polygon, Avalanche, Linea, Scroll, etc.

## Encrypted Wallet Storage (Python — Fernet)

Store wallets encrypted at rest. Never save private keys or mnemonics in plaintext.

```python
import json, os, base64, hashlib
from pathlib import Path
from cryptography.fernet import Fernet

REGISTRY_PATH = Path.home() / ".hermes" / "wallets.enc"

def _get_cipher(master_password: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(master_password.encode()).digest())
    return Fernet(key)

def save_wallet(label: str, chain: str, address: str, private_key: str,
                mnemonic: str, master_password: str):
    cipher = _get_cipher(master_password)
    REGISTRY_PATH.parent.mkdir(exist_ok=True, parents=True)
    registry = load_registry(master_password) if REGISTRY_PATH.exists() else {}
    registry[label] = {
        "chain": chain,
        "address": address,
        "private_key_enc": cipher.encrypt(private_key.encode()).decode(),
        "mnemonic_enc": cipher.encrypt(mnemonic.encode()).decode(),
    }
    REGISTRY_PATH.write_bytes(cipher.encrypt(json.dumps(registry).encode()))

def load_registry(master_password: str) -> dict:
    cipher = _get_cipher(master_password)
    return json.loads(cipher.decrypt(REGISTRY_PATH.read_bytes()).decode())
```

## Constraints

- **On-Chain Task Protocol (from SOUL.md — always active):**
  1. **Verifikasi sebelum execute** — cek contract address, token, amount, chain ID. Jangan assume.
  2. **Dry-run / simulate dulu** — `wallet.call(tx)` sebelum broadcast. Kalau simulate revert, jangan push.
  3. **Screenshot bukti** — capture tx confirmation screen atau tx hash setelah broadcast.
  4. **Cek tx hash di explorer** — konfirmasi tx success (status=1), bukan cuma "submitted."
  5. **Jangan pernah fabricate tx hash atau status** — kalau gagal, report gagal. Jangan claim success tanpa bukti explorer.
  6. **Estimasi gas wajib dicek** — kalau gas fee abnormal tinggi (>2x usually), alert sebelum proceed.
- ALWAYS simulate before broadcasting on mainnet
- Use `pending` nonce on parallel sends
- RPC fallback list, never a single endpoint for production
- Never log private keys (use `***` mask)
- Always use FallbackProvider or rotation for read calls at scale
- `.env` for secrets, never inline
- Test on testnet (Sepolia/Base Sepolia) before mainnet for any new flow
- Gas buffer 20% above estimate
- For batch ops: include retry on transient errors, p-limit for concurrency
- **Python sandbox f-string pitfall**: In `execute_code`, f-strings containing `***` (masked secrets) cause `SyntaxError: unterminated string literal`. Use string concatenation (`"Bearer " + token`) instead of f-strings (`f"Bearer {token}"`) when the value might contain `***`.