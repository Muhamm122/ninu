# EVM Wallet Creation — Quick Reference

## Generate New Wallet (Python)

```python
from eth_account import Account
import json

Account.enable_unaudited_hdwallet_features()

# 24-word mnemonic (recommended for production)
acct, mnemonic = Account.create_with_mnemonic(num_words=24, passphrase="")

wallet = {
    "chain": "EVM",
    "address": acct.address,
    "private_key": "0x" + acct.key.hex(),
    "mnemonic": mnemonic,
    "derivation_path": "m/44'/60'/0'/0/0"
}
```

## Encrypt and Store

```python
import json, os, base64, hashlib
from pathlib import Path
from cryptography.fernet import Fernet

REGISTRY_PATH = Path.home() / ".hermes" / "wallets.enc"
MASTER_PASSWORD=os.env...D", "hermes-default-change-me")

key = base64.urlsafe_b64encode(hashlib.sha256(MASTER_PASSWORD.encode()).digest())
cipher = Fernet(key)

registry = {}
label = "evm-main"
registry[label] = {
    "chain": "EVM",
    "address": wallet["address"],
    "private_key_enc": cipher.encrypt(wallet["private_key"].encode()).decode(),
    "mnemonic_enc": cipher.encrypt(wallet["mnemonic"].encode()).decode(),
    "derivation_path": wallet["derivation_path"],
}

REGISTRY_PATH.parent.mkdir(exist_ok=True, parents=True)
REGISTRY_PATH.write_bytes(cipher.encrypt(json.dumps(registry).encode()))
print("Wallet saved: " + wallet["address"])
```

## Chain Support

Same address works on ALL EVM chains:
- Ethereum, BSC, Base, Arbitrum, Optimism
- Polygon, Avalanche, Linea, Scroll
- Any EVM-compatible L2

## Security Rules

1. NEVER log private keys or mnemonics in chat output
2. ALWAYS encrypt before saving to disk
3. ALWAYS backup mnemonic offline (paper, metal plate)
4. Use *** mask when displaying keys: 0x2436...c04a
5. Test with small amounts before using for real operations
