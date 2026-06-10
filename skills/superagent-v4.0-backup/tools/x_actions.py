#!/usr/bin/env python3
"""
CUPANG X Actions Wrapper
Integrates Aripin's x-actions (API + browser fallback) with CUPANG tools.

Usage:
  python3 x_actions.py like <tweet_id>
  python3 x_actions.py retweet <tweet_id>
  python3 x_actions.py post "text"
  python3 x_actions.py quote <tweet_id> "text"
  python3 x_actions.py reply <tweet_id> "text"
  python3 x_actions.py follow <user_id>
  python3 x_actions.py follow_handle <@handle>
  python3 x_actions.py user <@handle>
  python3 x_actions.py garap <@handle> [tweet_id]
  python3 x_actions.py status
"""

import sys
import os

# Add x-actions to path
sys.path.insert(0, '/home/ubuntu/x-actions-aripin')
os.chdir('/home/ubuntu/x-actions-aripin')

from x_auto import (
    like, retweet, post, quote_tweet, reply, follow, 
    airdrop_follow, garap_full, user_lookup, status,
    ACCOUNTS, get_available_account
)
import json

def main():
    if len(sys.argv) < 2:
        print("CUPANG X Actions")
        print(f"Account: {ACCOUNTS[0]['handle'] if ACCOUNTS else 'none'}")
        print()
        print("Commands: like, retweet, post, quote, reply, follow, follow_handle, user, garap, status")
        return
    
    cmd = sys.argv[1]
    
    # Mark account as warmed (skip warm-up posts)
    if ACCOUNTS:
        ACCOUNTS[0]['warm'] = True
    
    if cmd == 'status':
        status()
    elif cmd == 'like':
        print(json.dumps(like(sys.argv[2]), indent=2, default=str))
    elif cmd == 'retweet':
        print(json.dumps(retweet(sys.argv[2]), indent=2, default=str))
    elif cmd == 'post':
        print(json.dumps(post(sys.argv[2]), indent=2, default=str))
    elif cmd == 'quote':
        print(json.dumps(quote_tweet(sys.argv[2], sys.argv[3]), indent=2, default=str))
    elif cmd == 'reply':
        print(json.dumps(reply(sys.argv[2], sys.argv[3]), indent=2, default=str))
    elif cmd == 'follow':
        print(json.dumps(follow(sys.argv[2]), indent=2, default=str))
    elif cmd == 'follow_handle':
        print(json.dumps(airdrop_follow(sys.argv[2]), indent=2, default=str))
    elif cmd == 'user':
        print(json.dumps(user_lookup(sys.argv[2]), indent=2, default=str))
    elif cmd == 'garap':
        tid = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(garap_full(sys.argv[2], tid), indent=2, default=str))
    else:
        print(f"Unknown: {cmd}")

if __name__ == '__main__':
    main()
