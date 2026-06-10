---
name: cc-generator
description: Generate valid Luhn credit card numbers with fake data for testing/dev. Supports UnionPay, Visa, Mastercard, Amex. Output is clean copy-paste format — never stored to files. For payment gateway testing, form validation, dev environments only.
triggers:
  - "generate cc"
  - "buat cc"
  - "cc generator"
  - "fake cc"
  - "unionpay"
  - "test card"
  - "credit card number"
---

# CC Generator

Generate valid Luhn credit card numbers with fake supporting data (name, expiry, CVV).

## Supported Networks

| Network | BIN Prefix | Length | CVV |
|---------|-----------|--------|-----|
| UnionPay | 62xx, 624-626, 628x | 16 | 3 |
| Visa | 4xxx | 16 | 3 |
| Mastercard | 5xxx, 2221-2720 | 16 | 3 |
| Amex | 34xx, 37xx | 15 | 4 |

## Usage

```bash
# UnionPay (default)
python3 ~/.hermes/scripts/unionpay_gen.py [count]

# Generic multi-network
python3 ~/.hermes/scripts/cc_gen.py [count] [--network unionpay|visa|mastercard|amex]
```

## Output Format

Clean copy-paste, no JSON, no file storage:

```
💳 Card #1
Number  : 6282193215151621
Name    : AISHA CHOI
Expiry  : 04/27
CVV     : 277
```

## Rules

- **Never store output to files** — display inline only
- **Never log full card numbers** in memory or logs
- Default count: 1, max: 100
- All numbers pass Luhn validation
- Names are random multicultural (Asian, Western, Arabic, Hispanic)
- Expiry: 6 months to 5 years from now

## Scripts

- `~/.hermes/scripts/unionpay_gen.py` — UnionPay only, optimized
- `~/.hermes/scripts/cc_gen.py` — Multi-network (if created)

## ⚠️ Disclaimer

Fake data only. Numbers pass Luhn but are NOT registered with any bank. For testing/development purposes only.
