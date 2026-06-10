#!/usr/bin/env python3
"""
IG Post Analyzer — Analyze engagement from Instagram feed data.

Usage:
  python3 ig_post_analyzer.py <feed_json_file> [followers]

Reads Instagram feed JSON (from i.instagram.com/api/v1/feed/user/) and outputs:
- Top posts by likes
- Engagement stats (avg likes, comments, engagement rate)
- Content type breakdown (photo vs video vs carousel)
- Keyword analysis from captions
- Likes distribution histogram

Example:
  python3 ig_post_analyzer.py /tmp/ig_feed.json 3533
"""

import json
import re
import sys
from collections import Counter

def analyze(filepath, followers=None):
    with open(filepath) as f:
        data = json.load(f)
    
    items = data.get('items', [])
    if not items:
        print("No items found in feed data")
        return
    
    posts = []
    for item in items:
        code = item.get('code', '')
        likes = item.get('like_count', 0)
        comments = item.get('comment_count', 0)
        caption_data = item.get('caption', {}) or {}
        caption = caption_data.get('text', '') if isinstance(caption_data, dict) else ''
        timestamp = item.get('taken_at', 0)
        media_type = item.get('media_type', 0)
        view_count = item.get('view_count', 0)
        
        type_str = {1: 'photo', 2: 'video', 8: 'carousel'}.get(media_type, 'unknown')
        type_emoji = {1: '📷', 2: '🎬', 8: '📚'}.get(media_type, '❓')
        
        posts.append({
            'code': code,
            'likes': likes,
            'comments': comments,
            'caption': caption[:300],
            'type': type_str,
            'type_emoji': type_emoji,
            'views': view_count,
            'timestamp': timestamp,
        })
    
    posts.sort(key=lambda x: x['likes'], reverse=True)
    
    print(f"\n{'='*60}")
    print(f"🏆 TOP POSTS BY LIKES ({len(posts)} posts)")
    print(f"{'='*60}")
    for i, p in enumerate(posts[:20]):
        engagement = p['likes'] + p['comments']
        print(f"\n  #{i+1} {p['type_emoji']} instagram.com/p/{p['code']}")
        print(f"     ❤️ {p['likes']} likes | 💬 {p['comments']} comments | 👁 {p['views']} views")
        if p['caption']:
            print(f"     Caption: {p['caption'][:120]}")
    
    total_likes = sum(p['likes'] for p in posts)
    total_comments = sum(p['comments'] for p in posts)
    total_views = sum(p['views'] for p in posts)
    
    print(f"\n{'='*60}")
    print(f"📊 STATS")
    print(f"{'='*60}")
    print(f"  Posts: {len(posts)}")
    print(f"  Total likes: {total_likes}")
    print(f"  Total comments: {total_comments}")
    print(f"  Total views: {total_views}")
    if posts:
        print(f"  Avg likes/post: {total_likes/len(posts):.1f}")
        print(f"  Avg comments/post: {total_comments/len(posts):.1f}")
    
    photos = [p for p in posts if p['type'] == 'photo']
    videos = [p for p in posts if p['type'] == 'video']
    carousels = [p for p in posts if p['type'] == 'carousel']
    
    print(f"\n📁 BY TYPE: 📷 {len(photos)} | 🎬 {len(videos)} | 📚 {len(carousels)}")
    if photos:
        print(f"  📷 Photo avg: {sum(p['likes'] for p in photos)/len(photos):.0f} likes")
    if videos:
        print(f"  🎬 Video avg: {sum(p['likes'] for p in videos)/len(videos):.0f} likes, {sum(p['views'] for p in videos)/len(videos):.0f} views")
    if carousels:
        print(f"  📚 Carousel avg: {sum(p['likes'] for p in carousels)/len(carousels):.0f} likes")
    
    if followers:
        avg_eng = (total_likes + total_comments) / len(posts) if posts else 0
        rate = (avg_eng / followers) * 100
        print(f"\n📈 ENGAGEMENT RATE: {rate:.2f}% (avg {avg_eng:.0f} / {followers} followers)")
    
    # Keywords
    all_captions = ' '.join(p['caption'].lower() for p in posts if p['caption'])
    words = re.findall(r'\b[a-z]{3,}\b', all_captions)
    stop = {'the','and','for','are','but','not','you','all','can','had','her','was','one','our','out','has','have','been','will','with','this','that','from','they','more','some','very','what','when','who','how','its','also','your','their','there','which','about','would','could','should','into','just','than','then','them','these','those','being','other','after','before','through','between','under','over','such','each','only','most','like','make','made','get','got','new','now','way','may','say','she','too','use','him','his','did','does','don','com','www','http','https','html','jpg','png','order','bisa','dan','yang','untuk','dengan','ini','itu','atau','juga','sudah','saja','lagi','kami','kita','anda','akan','ada','tidak','bukan','oleh','karena','seperti','namun','tetapi','serta'}
    keywords = [w for w in words if w not in stop and len(w) > 3]
    top_kw = Counter(keywords).most_common(15)
    if top_kw:
        print(f"\n🔑 TOP KEYWORDS:")
        for kw, count in top_kw:
            print(f"   {kw}: {count}x")
    
    # Distribution
    print(f"\n📊 LIKES DISTRIBUTION:")
    ranges = [(0,0), (1,5), (6,10), (11,20), (21,50), (51,100), (101,99999)]
    for lo, hi in ranges:
        count = len([p for p in posts if lo <= p['likes'] <= hi])
        if count > 0:
            label = f"{lo}" if lo == hi else f"{lo}-{hi}"
            bar = '█' * count
            print(f"  {label:>8} likes: {bar} ({count})")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    filepath = sys.argv[1]
    followers = int(sys.argv[2]) if len(sys.argv) > 2 else None
    analyze(filepath, followers)
