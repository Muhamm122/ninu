# IG Username Availability Checker

## Working Endpoint

```
GET https://i.instagram.com/api/v1/users/web_profile_info/?username=TARGET
Header: X-IG-App-ID: 936619743392459
```

## Response Interpretation

| HTTP Status | Body Contains | Meaning |
|-------------|---------------|---------|
| 200 | `"user":null` | ✅ Username AVAILABLE |
| 200 | `"id"` field | ❌ Username TAKEN (check `edge_followed_by.count` for followers) |
| 401 | — | Rate limited — wait and retry |
| 404 | — | Likely available (treat same as available) |

## App IDs to Rotate

```
936619743392459
735923892429730
567067343354431
```

## Best Practices

- **Delay 8-10s** between requests to avoid rate limiting
- **Batch size**: max ~20 usernames before hitting 401
- **After 401**: wait 3-5 minutes, then try with different App ID
- **AWS/datacenter IPs**: rate limited more aggressively — consider residential proxy for bulk checks
- **Accuracy**: This endpoint has been reliable as of 2025-06

## Failed Approaches

- `instagram.com/<username>/` web page → redirects to login wall (302)
- GraphQL `query_hash` endpoint → deprecated (returns 400)
- `instagram.com/<username>/?__a=1` → requires auth
- Third-party viewers (picuki, imginn) → 403 Cloudflare
- SocialBlade → 403 from datacenter IPs
- Google search → 403 captcha from datacenter IPs

## Full Name/Profile Extraction (when taken)

```python
import json, requests
resp = requests.get(
    f"https://i.instagram.com/api/v1/users/web_profile_info/?username={uname}",
    headers={
        "User-Agent": "Mozilla/5.0 ...",
        "X-IG-App-ID": "936619743392459"
    }
)
data = resp.json()
user = data.get("data", {}).get("user")
if user:
    followers = user.get("edge_followed_by", {}).get("count", "?")
    full_name = user.get("full_name", "")
    is_private = user.get("is_private", False)
    bio = user.get("biography", "")[:80]
```
