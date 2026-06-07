#!/usr/bin/env python3
"""
Dummy CC Generator — Luhn-valid fake credit card numbers.
Use for testing payment forms, API validation, etc.
NOT for real transactions — these are syntactically valid but not real accounts.

Usage:
    python3 cc_gen.py [BIN] [COUNT]
    python3 cc_gen.py 6233586370 5
"""
import json
import random


def generate_luhn(prefix: str, length: int = 16) -> str:
    """Generate a Luhn-valid card number from a BIN prefix."""
    digits = [int(d) for d in prefix]
    while len(digits) < length - 1:
        digits.append(random.randint(0, 9))
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    check = (10 - (total % 10)) % 10
    digits.append(check)
    return ''.join(str(d) for d in digits)


def generate_cc(bin_number: str, count: int = 5) -> list:
    """Generate multiple dummy CCs from a BIN."""
    cards = []
    for _ in range(count):
        card_num = generate_luhn(bin_number, 16)
        mm = str(random.randint(1, 12)).zfill(2)
        yy = str(random.randint(26, 30))
        cvc = str(random.randint(100, 999))
        cards.append({"card": card_num, "mm": mm, "yy": yy, "cvc": cvc})
    return cards


if __name__ == "__main__":
    import sys
    bin_arg = sys.argv[1] if len(sys.argv) > 1 else "424242424242"
    count_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    cards = generate_cc(bin_arg, count_arg)
    print(json.dumps({"bin": bin_arg, "cards": cards}, indent=2))
