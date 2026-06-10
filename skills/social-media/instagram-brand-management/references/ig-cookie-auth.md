# IG Cookie-Based Authentication (Server/VPS)

## When to Use

When the user wants the agent to manage IG directly from VPS (not just prep content), and provides cookies from their browser.

## Cookie Export Format

User exports from browser as JSON (DevTools → Application → Cookies → copy all). Format:
```json
[{"name": "sessionid", "value": "...", "domain": ".instagram.com"}, ...]
```

### Critical Cookies (minimum required)

| Cookie | Purpose | Required For |
|--------|---------|-------------|
| `sessionid` | Main auth token | All operations |
| `csrftoken` | POST request validation | All operations |
| `ds_user_id` | User ID | All operations |
| `mid` | Machine ID | All operations |
| `datr` | Browser fingerprint | Read operations |
| `rur` | Regional/routing cookie | **Write operations (upload, post, story)** |
| `ig_did` | Device ID | Recommended |

### ⚠️ The `rur` Cookie — Critical for Upload/Post

**`rur` is required for all write operations** (photo upload, story posting, etc.). Without it, IG returns:
```
HTTP 412 — AuthorizationFailedError: "A temporary failure has occurred. Please try again."
```

This error is **retriable** but will keep failing without `rur`. No amount of retrying, header rotation, or endpoint switching will fix it.

**How to get `rur`**: Export cookies from browser using DevTools → Application → Cookies → `https://www.instagram.com`. Look for the `rur` entry. It's a long string like `"HIL\05460988187971\0541812444947:01ff29a1..."`.

**Common pitfall**: Some cookie export extensions/tools redact `rur` as `***`. If your cookies.txt has `rur ***`, it's invalid — you need the real value. Use "EditThisCookie" extension or DevTools manual copy.

**Cookie export checklist**:
- [ ] `sessionid` — present and complete
- [ ] `csrftoken` — present and complete
- [ ] `ds_user_id` — present
- [ ] `mid` — present
- [ ] `datr` — present
- [ ] `rur` — present and NOT redacted (`***`)
- [ ] `ig_did` — present (recommended)

### Convert JSON → Netscape cookies.txt

Use Hermes to convert (write to `~/.hermes/<brand>/ig-cookies.txt`):
```
.instagram.com  TRUE  /  TRUE  <expiry>  <name>  <value>
```

**Never paste cookie values in chat** — write directly to file.

## What Works from VPS (Updated June 2026)

### Auth Verification
```
GET https://www.instagram.com/accounts/edit/
```
- Returns 200 + 800KB+ HTML with username embedded
- Parse: `re.search(r'"username":"([^"]+)"', html)`
- This works reliably from datacenter IPs

### User Profile Info
```
GET https://i.instagram.com/api/v1/users/web_profile_info/?username=USERNAME
Headers:
  User-Agent: Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229258)
  X-IG-App-ID: 1217981644879628
  X-CSRFToken: <from cookie>
  Cookie: <netscape format>
```
- Returns full user profile JSON (followers, following, bio, profile pic, etc.)
- **Use curl, NOT Python urllib** — urllib gets 429, curl gets 200
- Mobile API endpoint (`i.instagram.com`) works; web endpoint (`www.instagram.com/api/`) gets 429

### User Feed / Posts
```
GET https://i.instagram.com/api/v1/feed/user/{user_id}/?count=50
Headers: same as above
```
- Returns posts with likes, comments, captions, media type, timestamps
- **Pagination**: Use `&max_id={next_max_id}` from response
- Response includes `more_available: true/false` and `next_max_id`
- Typical: 12 posts per batch

### What Still Requires Residential Proxy (or Fails from VPS)
- **Photo/video upload** → HTTP 412 (missing `rur` cookie) or HTTP 429 (rate limit even with `rur`)
- **Story/reel creation** → HTTP 412/429
- **Follow/unfollow** → HTTP 429
- **Like/comment on other posts** → HTTP 429
- **DM operations** → HTTP 429
- **Viewing private profiles** → HTTP 429

**Note**: Even with all cookies including `rur`, write operations from datacenter IPs may still get 429. The `rur` cookie is *necessary* but not *sufficient* — IG also checks IP reputation. For reliable posting, use a residential proxy or post from a real device.

## Rate Limit Behavior

| Endpoint | From VPS | Notes |
|----------|----------|-------|
| `accounts/edit/` | 200 | HTML page, no rate limit |
| `i.instagram.com/api/v1/users/web_profile_info/` | 200 | With mobile UA + app ID |
| `i.instagram.com/api/v1/feed/user/` | 200 | With mobile UA + app ID |
| `www.instagram.com/api/v1/*` | 429 | Web API blocked from DC IPs |
| `i.instagram.com/api/v1/media/*/like/` | 429 | Write ops blocked |
| `i.instagram.com/api/v1/accounts/*` | 429 | Write ops blocked |

**Key insight**: Mobile API (`i.instagram.com`) with Android User-Agent and `X-IG-App-ID: 1217981644879628` works for **read-only** operations from datacenter IPs. Write operations are always blocked.

## Post Analysis Workflow

Once you have feed data, analyze engagement:

```python
# Load feed JSON
for item in data['items']:
    code = item.get('code')
    likes = item.get('like_count', 0)
    comments = item.get('comment_count', 0)
    caption = item.get('caption', {}).get('text', '')
    media_type = item.get('media_type')  # 1=photo, 2=video, 8=carousel
    views = item.get('view_count', 0)  # videos only
    timestamp = item.get('taken_at')

# Sort by likes for top posts
# Calculate engagement rate: (likes + comments) / followers * 100
# Analyze caption keywords for content themes
# Compare photo vs video vs carousel performance
```

## Browser Cookie Injection (June 2026)

When using Hermes browser tools (cloakbrowser) to navigate IG:

### What Works
- Inject non-httpOnly cookies via `document.cookie = "name=value; domain=.instagram.com; path=/; secure"`
- Injectable: `csrftoken`, `ds_user_id`, `ps_n`, `ps_l`, `dpr`, `wd`
- Browser navigates IG pages successfully after injection (title, content load correctly)

### What Doesn't Work
- httpOnly cookies (`sessionid`, `mid`, `datr`, `rur`) **cannot** be set via `document.cookie`
- These are blocked by browser security policy
- CDP `Network.setCookie` is not available from browser console (`typeof CDP === 'undefined'`)

### Workaround for Full Auth
- Start browser with cookie file at launch (if supported by cloakbrowser config)
- Or use API approach (curl + cookies.txt) for read operations
- For write operations (upload, post), need `rur` cookie — must get from user's browser export

### IG Story via Browser UI — Not Feasible
- Desktop web UI "New post" → "Create" menu has: Post, Live video, Ad, AI — **no Story option**
- Stories are created via mobile app or the `+` button in the stories tray (left side of home)
- Even if you navigate to `/stories/create/`, IG redirects to view someone else's story
- **Conclusion**: Story creation via browser automation is impractical; use API with proper cookies or have user post manually

## curl vs urllib — Critical Difference

**`curl` gets 200, Python `urllib` gets 429** for the same `i.instagram.com` endpoint with identical headers.

Likely cause: `curl` sends different default headers:
- `Accept: */*` (curl default) vs `Accept: text/html,...` (urllib default)
- `Accept-Encoding: gzip, deflate` (curl) vs none (urllib)
- Different TCP/TLS fingerprint

**Always use `curl` for IG API calls from VPS.** If you must use Python, try `requests` library with curl-like headers, or shell out to `curl` via `subprocess`.

## Shell Gotchas

### Python Heredoc with `&` Characters
```bash
# THIS FAILS — shell interprets & as background operator
python3 << 'PYEOF'
curl -s "url" -o file -w "%{http_code}"
PYEOF
```

**Fix**: Write Python to file first, then execute:
```bash
cat > /tmp/script.py << 'EOF'
# Python code here
EOF
python3 /tmp/script.py
```

### Long Pipes Timeout
```bash
# THIS TIMES OUT for large responses
curl -s "url" | python3 -c "import sys,json; json.load(sys.stdin)"
```

**Fix**: Save to file first, then analyze:
```bash
curl -s "url" -o /tmp/response.json -w "%{http_code}"
python3 /tmp/analyze.py  # reads /tmp/response.json
```

## Security Notes

- Cookies = full account access. Treat as passwords.
- If cookies are accidentally exposed in chat: user must logout all devices + change password immediately
- Store cookies file with restricted permissions: `chmod 600 ig-cookies.txt`
- Never commit cookies to git or include in backups
- Never paste cookie values in chat — write directly to file
