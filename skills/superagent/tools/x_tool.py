#!/usr/bin/env python3
"""
X/Twitter CLI Tool — CUPANG AI AGENT
Cookies-based auth via @muhamm122
Usage: python3 x_tool.py <command> [args]
Commands: profile, post, timeline, search, like, retweet, follow, whoami
"""

import requests
import json
import re
import sys
import os
import time
from datetime import datetime
from urllib.parse import quote

# ===================== AUTH =====================
AUTH_TOKEN = os.getenv('X_AUTH_TOKEN', 'db9e9b7e2d5fc2d27c0f5f3bb4edea86373f5169')
CT0 = os.getenv('X_CT0', 'cbbd319ca8e37abb7ca81a251892401c4d0341f6bfa52b0ff884d8993429b98899f69da0a0fc0b71d06887734bf31fa5b0edf0f9ece987b701bd7a95c3a4ae6a27c46f3c3dcdd7ba0284337f44d31c7a')
BEARER = 'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'
USER_ID = '1205811165873332225'
HANDLE = '@muhamm122'

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

def get_session():
    s = requests.Session()
    s.cookies.set('auth_token', AUTH_TOKEN, domain='.x.com')
    s.cookies.set('ct0', CT0, domain='.x.com')
    s.cookies.set('twid', f'u%3D{USER_ID}', domain='.x.com')
    # Don't set Authorization header for page requests — 
    # only use Bearer for API calls
    return s

# ===================== COMMANDS =====================

def whoami():
    """Quick check if cookies are still valid"""
    s = get_session()
    r = s.get('https://x.com/home', headers={'User-Agent': UA}, timeout=10)
    text = r.text
    handle = re.search(r'"screen_name":"(\w+)"', text)
    name = re.search(r'"name":"(.+?)"', text)
    if handle:
        print(f"✅ Logged in as @{handle.group(1)}")
        if name:
            print(f"   Display name: {name.group(1)}")
        return True
    else:
        print("❌ Not logged in — cookies expired")
        return False

def profile():
    """Get own profile info"""
    s = get_session()
    r = s.get('https://x.com/home', headers={'User-Agent': UA}, timeout=10)
    text = r.text
    
    fields = ['screen_name', 'name', 'id_str', 'followers_count', 
              'friends_count', 'statuses_count', 'description', 'location',
              'created_at', 'verified', 'profile_image_url_https']
    
    found = {}
    for key in fields:
        match = re.search(rf'"{key}"\s*:\s*"?(.+?)"?[,\}}]', text)
        if match:
            found[key] = match.group(1)
    
    print(f"🐦 X Profile: @{found.get('screen_name', 'N/A')}")
    print(f"   Name: {found.get('name', 'N/A')}")
    print(f"   ID: {found.get('id_str', 'N/A')}")
    print(f"   Followers: {found.get('followers_count', '0')}")
    print(f"   Following: {found.get('friends_count', '0')}")
    print(f"   Tweets: {found.get('statuses_count', '0')}")
    print(f"   Bio: {found.get('description', '(none)')}")
    print(f"   Location: {found.get('location', '(none)')}")
    print(f"   Created: {found.get('created_at', 'N/A')}")
    print(f"   Verified: {found.get('verified', 'false')}")
    return found

def post(text):
    """Post a tweet"""
    if not text:
        print("Usage: post <tweet text>")
        return
    
    s = get_session()
    # Use GraphQL CreateTweet
    variables = json.dumps({"tweet_text": text, "dark_request": False})
    features = json.dumps({
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_side_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "tweetypie_tweet_mention_api_enabled": True,
    })
    
    url = f"https://api.x.com/graphql/H-t2v_HvFR07ZBP9aOeKoA/CreateTweet?variables={quote(variables)}&features={quote(features)}"
    
    r = s.post(url, timeout=15)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        if 'data' in data:
            tweet_result = data['data'].get('create_tweet', {}).get('tweet_results', {}).get('result', {})
            tweet_id = tweet_result.get('rest_id', 'unknown')
            print(f"✅ Tweet posted! ID: {tweet_id}")
            print(f"   Text: {text[:100]}")
            return tweet_id
        else:
            print(f"❌ Failed: {json.dumps(data)[:300]}")
    except:
        print(f"Response: {r.text[:300]}")

def search(query, count=5):
    """Search tweets"""
    if not query:
        print("Usage: search <query>")
        return
    
    s = get_session()
    variables = json.dumps({
        "rawQuery": query,
        "count": count,
        "querySource": "typed_query",
        "product": "Top"
    })
    features = json.dumps({
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_count_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
    })
    
    url = f"https://api.x.com/graphql/Yw6L66Pw54NHKuq4Dp7b4Q/SearchTimeline?variables={quote(variables)}&features={quote(features)}"
    
    r = s.get(url, timeout=15)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2)[:1000])
    except:
        print(r.text[:500])

def timeline(count=5):
    """Get home timeline"""
    s = get_session()
    variables = json.dumps({"count": count, "includePromotedContent": True})
    features = json.dumps({
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_count_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "view_counts_everywhere_api_enabled": True,
    })
    
    url = f"https://api.x.com/graphql/7zlnp2TxC044W4C1ZUJMHw/HomeTimeline?variables={quote(variables)}&features={quote(features)}"
    
    r = s.get(url, timeout=15)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2)[:1000])
    except:
        print(r.text[:500])

# ===================== CLI =====================

COMMANDS = {
    'whoami': lambda args: whoami(),
    'profile': lambda args: profile(),
    'post': lambda args: post(' '.join(args)),
    'search': lambda args: search(' '.join(args)),
    'timeline': lambda args: timeline(),
}

def main():
    if len(sys.argv) < 2:
        print("X/Twitter CLI — CUPANG AI AGENT")
        print(f"Account: {HANDLE}")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        return
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd in COMMANDS:
        COMMANDS[cmd](args)
    elif cmd == 'help':
        print("Commands:", ', '.join(COMMANDS.keys()))
    else:
        print(f"Unknown command: {cmd}")
        print("Available:", ', '.join(COMMANDS.keys()))

if __name__ == '__main__':
    main()
