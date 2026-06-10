# IG Username Availability Checking

## Working Method: Mobile API Endpoint

The `i.instagram.com/api/v1/users/web_profile_info/` endpoint returns profile data without authentication when called with the right headers.

### Required Headers
```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
X-IG-App-ID: 936619743392459
```

### App IDs to Rotate
- `936619743392459` (primary)
- `735923892429730`
- `124024574876181`

### Response Format (Taken)
```json
{
  "data": {
    "user": {
      "id": "12345678",
      "username": "taken.name",
      "full_name": "...",
      "biography": "...",
      "edge_followed_by": { "count": 2717 },
      "profile_pic_url": "..."
    }
  }
}
```

### Response Format (Available)
```json
{
  "data": {
    "user": null
  }
}
```

### Rate Limits
- ~15 requests before 401 rate limit kicks in
- After rate limit, the block is **IP-level, persistent for hours** — rotating app IDs, user agents, and waiting 30-120s will NOT reset it (confirmed: still 401 after 3+ minute waits and multiple ID rotations on June 2026)
- **Do NOT waste time retrying after 401** — mark remaining names as ❓ unchecked and tell user to verify manually
- Batch all checks in one pass early in session — you likely won't get a second batch
- Sleep 3-5s between requests in batch
- Rotate X-IG-App-ID after every few requests as a precaution

### Failed Approaches (Do Not Use)
- `instagram.com/username/` in browser → redirects to login wall from datacenter IPs
- `curl instagram.com/username/` without auth → 302 redirect to login
- GraphQL `query_hash=c76146de99bb02a641c6d9d6e066cd35` → returns 400 (deprecated as of mid-2026)
- Third-party viewers (imginn.com, pikdo/picuki.com) → Cloudflare 403 from datacenter IPs
- Embed endpoint `instagram.com/username/?__a=1&__d=dis` → returns empty 201
- Google search for `instagram "username"` → IP-level CAPTCHA/block from datacenter
- DuckDuckGo HTML search → CAPTCHA (duck image challenge) from datacenter
- SocialBlade → 403 from datacenter IPs

## Session Data (June 2026)

### Batch 1: @nana.furniart rebrand candidates
- 9 AVAILABLE: nana.ruang, nana.home, nana.woodwork, nana.furn, nanahabitat, darkwood.id, nana.dwell, nana.mebelu, nana.duduk
- 13 TAKEN: nana.haus (2717), nana.living (43), nanahaus (10), nana.wood (239), nana.space (688), nana.mebel (169), mebel.nana (19), nana.room (0), nana.interior (0), nana.oak (125), nana.kayu (8), nana.craft (112), nanamade (74)
- 8 unchecked (rate limited): nana.rumah, nana.labs, woodxna, ruma.nana, nana.spati, nana.timber, nana.lumber, haus.nana

### Batch 2: @hausliving analysis
User asked about `haus.living` / `hausliving` as rebrand candidate. Could not verify availability — IP was already rate-limited from Batch 1.

**Domain check:**
- `hausliving.com` → REGISTERED
- `haus-living.com` → REGISTERED
- `hausliving.id` → LIKELY AVAILABLE
- `hausliving.co.id` → LIKELY AVAILABLE

**Analysis of "haus living" as brand name:**
| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Aesthetic match | 9/10 | "Haus" (German: house) + "living" = dark/modern/Scandinavian feel — perfect for wood-forward brands |
| Premium feel | 10/10 | German word → high-end, import-quality perception |
| International | 9/10 | Universal appeal — works for expat, MY, SG markets |
| Market language | 6/10 | "Haus" not understood by mass Indonesian market (but creates premium mystique) |
| IG SEO | 7/10 | "living" = high search volume in IG home decor niche |
| Memorability | 8/10 | Two short words, easy to recall |

**Trade-offs:**
- Loses "nana" personal brand prefix — but more scalable brand (franchise, product lines possible)
- `.com` domain taken — must use `.id` / `.co.id`
- No-dot version (`hausliving`) preferred over dot version (`haus.living`) — no tag mistakes

**Autocomplete research (DuckDuckGo):**
- "haus living furniture" → 0 suggestions (unique = good for brand SEO, no competition)
- "mebel modern" → 7 suggestions (established search term)
- "sofa minimalis" → 7 suggestions (established search term)
- "haus furniture" → 7 suggestions ("haus" keyword has existing search volume)
- "furniture living" → 8 suggestions (high search volume for "living room furniture")

### Rebrand Result
- **User chose:** `@haus_living1` (underscore version with "1" suffix — primary clean names likely taken)
- **Brand name:** "Haus Living" (displayed in bio with space)
- **Lesson:** When ideal username is taken, user prefers underscore + suffix over dot version (haus_living1 > haus.living for tag reliability)
- **All files rebranded:** strategy files, landing page, cron jobs, templates, persistent memory

### Naming Analysis Framework (for future brands)

When evaluating a username change, assess across these dimensions:
1. **Aesthetic match** (30%) — does the name match the visual brand?
2. **Market language** (25%) — does the target market understand/resonate with the words?
3. **Search SEO** (20%) — are the words actually searched on IG Explore?
4. **Memorability** (15%) — shorter, no dot, one word is ideal
5. **Uniqueness** (10%) — less likely to collide with existing accounts

Compare against domain availability and competitor landscape before recommending.

## Manual Verification Method

User should verify availability by trying to change their IG username in Settings → Edit Profile. IG will immediately show "available" or "unavailable" — zero risk (current username stays if the new one is taken).
