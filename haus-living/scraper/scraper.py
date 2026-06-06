#!/usr/bin/env python3
"""
Haus Living Multi-Purpose Scraper Toolkit
==========================================
Scrapers:
  1. IG Competitor Monitor — track competitor accounts, hashtags
  2. Price Monitor — monitor competitor prices on Tokopedia/Shopee
  3. Trend Scraper — Google Trends / keyword research
  4. Review Scraper — monitor reviews on marketplace
  5. News Scraper — furniture/home decor industry news

Usage:
  python3 scraper.py ig --hashtag "mebelminimalis" --limit 20
  python3 scraper.py price --keyword "sofa minimalis" --marketplace tokopedia
  python3 scraper.py trend --keyword "furniture jakarta"
  python3 scraper.py news --limit 10
  python3 scraper.py monitor --config monitor.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(os.path.expanduser("~/.hermes/haus-living/scraper-data"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}


def save_result(data, prefix):
    """Save scraped data as timestamped JSON."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"{prefix}_{ts}.json"
    fpath = OUTPUT_DIR / fname
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved: {fpath}")
    return str(fpath)


# ============================================================
# 1. INSTAGRAM SCRAPER (via web/API — no login required)
# ============================================================

def scrape_ig_hashtag(hashtag, limit=20):
    """Scrape IG hashtag page for recent posts (limited — IG walls most content)."""
    print(f"🔍 Scraping IG hashtag: #{hashtag}")
    results = []

    # Try the IG explore API endpoint
    try:
        url = f"https://i.instagram.com/api/v1/tags/{hashtag}/top/"
        resp = requests.get(url, headers={
            **HEADERS,
            "X-IG-App-ID": "936619743392459",
        }, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            sections = data.get("sections", [])
            for section in sections[:limit]:
                for item in section.get("layout_content", {}).get("medias", []):
                    media = item.get("media", {})
                    results.append({
                        "id": media.get("pk", ""),
                        "type": "video" if media.get("media_type") == 2 else "image",
                        "caption": media.get("caption", {}).get("text", "")[:200] if media.get("caption") else "",
                        "likes": media.get("like_count", 0),
                        "comments": media.get("comment_count", 0),
                        "timestamp": media.get("taken_at", 0),
                        "user": media.get("user", {}).get("username", ""),
                    })
        else:
            print(f"  ⚠️ API returned {resp.status_code} — trying web fallback")
            # Fallback: scrape the public web page
            web_url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            resp2 = requests.get(web_url, headers=HEADERS, timeout=10)
            if resp2.status_code == 200:
                # Try to extract data from embedded JSON
                match = re.search(r'window\._sharedData\s*=\s*({.+?});</script>', resp2.text)
                if match:
                    shared = json.loads(match.group(1))
                    # Extract basic hashtag info
                    tag_data = shared.get("entry_data", {}).get("TagPage", [{}])[0].get("graphql", {}).get("hashtag", {})
                    results.append({
                        "hashtag": hashtag,
                        "name": tag_data.get("name", hashtag),
                        "post_count": tag_data.get("edge_hashtag_to_media", {}).get("count", 0),
                        "top_posts": len(tag_data.get("edge_hashtag_to_top_posts", {}).get("edges", [])),
                    })
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Also try a DuckDuckGo search for the hashtag
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q=instagram+{hashtag}+furniture"
        resp3 = requests.get(ddg_url, headers=HEADERS, timeout=10)
        if resp3.status_code == 200:
            soup = BeautifulSoup(resp3.text, "html.parser")
            for result in soup.select(".result")[:limit]:
                title = result.select_one(".result__title")
                snippet = result.select_one(".result__snippet")
                link = result.select_one(".result__url")
                if title:
                    results.append({
                        "source": "duckduckgo",
                        "title": title.get_text(strip=True),
                        "snippet": snippet.get_text(strip=True) if snippet else "",
                        "url": link.get_text(strip=True) if link else "",
                    })
    except Exception:
        pass

    meta = {
        "type": "ig_hashtag",
        "hashtag": hashtag,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "results": results,
    }
    save_result(meta, f"ig_{hashtag}")
    return meta


# ============================================================
# 2. PRICE MONITOR (Tokopedia / Shopee)
# ============================================================

def scrape_prices(keyword, marketplace="tokopedia", limit=20):
    """Scrape product prices from marketplace."""
    print(f"🔍 Scraping prices for '{keyword}' on {marketplace}")
    results = []

    try:
        if marketplace == "tokopedia":
            # Tokopedia search API
            url = f"https://ace.tokopedia.com/search/v2.5/product/v4"
            params = {
                "q": keyword,
                "rows": limit,
                "start": 0,
                "source": "search",
                "device": "desktop",
                "related": "true",
                "catalog_rows": 5,
                "tft": 0,
                "ob": 23,  # sort by relevance
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("data", {}).get("products", [])
                for p in products[:limit]:
                    results.append({
                        "name": p.get("name", ""),
                        "price": p.get("price_int", 0),
                        "price_fmt": p.get("price", ""),
                        "rating": p.get("rating", "0"),
                        "sold": p.get("sold", 0),
                        "shop": p.get("shop", {}).get("name", "") if isinstance(p.get("shop"), dict) else "",
                        "url": f"https://www.tokopedia.com/{p.get('url', '').lstrip('/')}",
                        "image": p.get("image_url", ""),
                        "marketplace": "tokopedia",
                    })
            else:
                print(f"  ⚠️ Tokopedia API returned {resp.status_code}")

        elif marketplace == "shopee":
            # Shopee search (limited without API key)
            url = f"https://shopee.co.id/api/v4/recommend/recommend?keyword={quote_plus(keyword)}&limit={limit}"
            resp = requests.get(url, headers={
                **HEADERS,
                "X-Shopee-Language": "id",
                "X-API-SOURCE": "pc",
            }, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("items", [])
                for item in items[:limit]:
                    item_basic = item.get("item_basic", {})
                    results.append({
                        "name": item_basic.get("name", ""),
                        "price": item_basic.get("price", 0) // 100000,  # Shopee stores price * 100000
                        "rating": item_basic.get("item_star_rating", 0),
                        "sold": item_basic.get("historical_sold", 0),
                        "marketplace": "shopee",
                    })
            else:
                print(f"  ⚠️ Shopee API returned {resp.status_code}")

    except Exception as e:
        print(f"  ❌ Error: {e}")

    # If no results from API, try web scraping
    if not results:
        print("  🔄 API failed — trying web search fallback...")
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(keyword)}+harga+site:{marketplace}.co.id"
            resp = requests.get(ddg_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for r in soup.select(".result")[:limit]:
                    title = r.select_one(".result__title")
                    snippet = r.select_one(".result__snippet")
                    if title:
                        results.append({
                            "source": "duckduckgo_fallback",
                            "title": title.get_text(strip=True),
                            "snippet": snippet.get_text(strip=True) if snippet else "",
                            "marketplace": marketplace,
                        })
        except Exception:
            pass

    meta = {
        "type": "price_monitor",
        "keyword": keyword,
        "marketplace": marketplace,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "results": results,
    }
    save_result(meta, f"price_{marketplace}_{keyword.replace(' ','_')}")
    return meta


# ============================================================
# 3. TREND SCRAPER (keyword research)
# ============================================================

def scrape_trends(keyword, limit=10):
    """Scrape search trends and autocomplete for keyword research."""
    print(f"🔍 Scraping trends for '{keyword}'")
    results = {"keyword": keyword, "suggestions": [], "related": [], "news": []}

    # DuckDuckGo autocomplete
    try:
        url = f"https://duckduckgo.com/ac/?q={quote_plus(keyword)}&type=list"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 1:
                results["suggestions"] = data[1][:limit * 2]
    except Exception as e:
        print(f"  ⚠️ Autocomplete error: {e}")

    # Google Trends via serp (unofficial)
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(keyword)}+trend+indonesia+2024+2025"
        resp = requests.get(ddg_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for r in soup.select(".result")[:limit]:
                title = r.select_one(".result__title")
                snippet = r.select_one(".result__snippet")
                link = r.select_one(".result__url")
                if title:
                    results["related"].append({
                        "title": title.get_text(strip=True),
                        "snippet": snippet.get_text(strip=True) if snippet else "",
                        "url": link.get_text(strip=True) if link else "",
                    })
    except Exception as e:
        print(f"  ⚠️ Related search error: {e}")

    # News search
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(keyword)}+berita+furniture+indonesia"
        resp = requests.get(ddg_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for r in soup.select(".result")[:limit]:
                title = r.select_one(".result__title")
                snippet = r.select_one(".result__snippet")
                if title:
                    results["news"].append({
                        "title": title.get_text(strip=True),
                        "snippet": snippet.get_text(strip=True) if snippet else "",
                    })
    except Exception:
        pass

    meta = {
        "type": "trend_research",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        **results,
    }
    save_result(meta, f"trend_{keyword.replace(' ','_')}")
    return meta


# ============================================================
# 4. NEWS SCRAPER (furniture industry)
# ============================================================

def scrape_news(limit=10):
    """Scrape furniture/home decor industry news."""
    print(f"🔍 Scraping furniture news")
    results = []

    queries = [
        "furniture indonesia berita",
        "mebel kayu indonesia 2024",
        "home decor trend 2025",
    ]

    for q in queries:
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
            resp = requests.get(ddg_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for r in soup.select(".result")[:5]:
                    title = r.select_one(".result__title")
                    snippet = r.select_one(".result__snippet")
                    link = r.select_one(".result__url")
                    if title:
                        results.append({
                            "query": q,
                            "title": title.get_text(strip=True),
                            "snippet": snippet.get_text(strip=True) if snippet else "",
                            "url": link.get_text(strip=True) if link else "",
                        })
            time.sleep(1)  # Rate limit
        except Exception:
            continue

    meta = {
        "type": "news",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "results": results[:limit],
    }
    save_result(meta, "news_furniture")
    return meta


# ============================================================
# 5. MONITOR MODE (run all scrapers from config)
# ============================================================

def run_monitor(config_path):
    """Run all scrapers defined in a monitor config JSON."""
    print(f"🔍 Running monitor from {config_path}")
    with open(config_path) as f:
        config = json.load(f)

    all_results = []

    for task in config.get("tasks", []):
        task_type = task.get("type")
        print(f"\n  → {task_type}: {task.get('keyword', task.get('hashtag', ''))}")

        if task_type == "ig":
            r = scrape_ig_hashtag(task["hashtag"], task.get("limit", 20))
        elif task_type == "price":
            r = scrape_prices(task["keyword"], task.get("marketplace", "tokopedia"), task.get("limit", 20))
        elif task_type == "trend":
            r = scrape_trends(task["keyword"], task.get("limit", 10))
        elif task_type == "news":
            r = scrape_news(task.get("limit", 10))
        else:
            print(f"    ⚠️ Unknown type: {task_type}")
            continue

        all_results.append(r)
        time.sleep(task.get("delay", 3))

    print(f"\n✅ Monitor complete: {len(all_results)} tasks executed")
    return all_results


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Haus Living Scraper Toolkit")
    sub = parser.add_subparsers(dest="command", help="Scraper command")

    # IG
    ig_p = sub.add_parser("ig", help="Instagram hashtag scraper")
    ig_p.add_argument("--hashtag", "-t", required=True, help="Hashtag to scrape")
    ig_p.add_argument("--limit", "-l", type=int, default=20, help="Max results")

    # Price
    price_p = sub.add_parser("price", help="Price monitor")
    price_p.add_argument("--keyword", "-k", required=True, help="Product keyword")
    price_p.add_argument("--marketplace", "-m", default="tokopedia", choices=["tokopedia", "shopee"])
    price_p.add_argument("--limit", "-l", type=int, default=20)

    # Trend
    trend_p = sub.add_parser("trend", help="Trend/keyword research")
    trend_p.add_argument("--keyword", "-k", required=True)
    trend_p.add_argument("--limit", "-l", type=int, default=10)

    # News
    news_p = sub.add_parser("news", help="Furniture industry news")
    news_p.add_argument("--limit", "-l", type=int, default=10)

    # Monitor
    mon_p = sub.add_parser("monitor", help="Run all from config")
    mon_p.add_argument("--config", "-c", required=True, help="Monitor config JSON path")

    args = parser.parse_args()

    if args.command == "ig":
        result = scrape_ig_hashtag(args.hashtag, args.limit)
    elif args.command == "price":
        result = scrape_prices(args.keyword, args.marketplace, args.limit)
    elif args.command == "trend":
        result = scrape_trends(args.keyword, args.limit)
    elif args.command == "news":
        result = scrape_news(args.limit)
    elif args.command == "monitor":
        result = run_monitor(args.config)
    else:
        parser.print_help()
        return

    # Print summary
    if isinstance(result, dict):
        print(f"\n📊 Results: {result.get('count', len(result.get('results', [])))} items")


if __name__ == "__main__":
    main()
