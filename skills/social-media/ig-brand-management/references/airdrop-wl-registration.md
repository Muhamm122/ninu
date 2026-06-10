# Airdrop Whitelist Registration Pattern

Common pattern for crypto project WL/allowlist registrations that require X engagement + EVM wallet submission.

## Typical Task List

1. **Follow** the project's X account (e.g. @outworld3rs)
2. **Like & Quote** their announcement post
3. **Tag 2 friends** in the comments/replies
4. **Submit** EVM wallet address + X handle on the project's registration form

## Execution Strategy

### Phase 1: X Engagement (via Playwright with cookie injection)

```python
# Must inject httpOnly auth_token via context.add_cookies()
await context.add_cookies([
    {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com", "path": "/",
     "secure": True, "httpOnly": True, "sameSite": "None", "expires": 1812333299},
    {"name": "ct0", "value": CT0, "domain": ".x.com", "path": "/",
     "secure": True, "sameSite": "Lax", "expires": 1815357299},
    {"name": "twid", "value": f"u%3D{USER_ID}", "domain": ".x.com", "path": "/",
     "secure": True, "sameSite": "None", "expires": 1812333434},
])

page = await context.new_page()

# Follow: navigate to profile, click Follow button
await page.goto('https://x.com/TARGET_HANDLE', wait_until='commit', timeout=20000)
await asyncio.sleep(7)  # X React hydration needs time
follow_btn = page.get_by_role('button', name=re.compile(r'Follow', re.I)).first
await follow_btn.click()

# Like: find tweet, click like
like_btn = tweet.locator('[data-testid="like"]').first
await like_btn.click()

# Quote: retweet → Quote → type text → post
retweet_btn = tweet.locator('[data-testid="retweet"]').first
await retweet_btn.click()
quote_option = page.locator('[role="menuitem"]:has-text("Quote")').first
await quote_option.click()
textarea = page.locator('[data-testid="tweetTextarea_0"]').first
await textarea.fill("Your quote text @TARGET #hashtags")
post_btn = page.locator('[data-testid="tweetButtonInline"]').first
await post_btn.click()

# Reply with tags
reply_area = page.locator('[data-testid="tweetTextarea_0"]').first
await reply_area.fill("@friend1 @friend2 message")
reply_btn = page.locator('[data-testid="tweetButtonInline"]').first
await reply_btn.click()
```

### Phase 2: Form Submission (via browser — NOT requests)

WL forms are typically React SPAs. **Must use `browser_type` / Playwright locators** to fill inputs — `document.value = X` does NOT trigger React's onChange handler.

```
1. Navigate to registration URL
2. Click "REGISTER" / "SIGN UP" button to open modal
3. Use browser_type (Hermes) or locator.fill() (Playwright) to fill:
   - EVM wallet address (0x...)
   - X handle (@handle)
4. Click submit button
5. **Success indicator**: modal closes (no explicit success message in most WL forms)
```

## Pitfalls

### React SPA Forms Ignore Direct DOM Manipulation
- `document.getElementById('input').value = '0x...'` does NOT update React state
- The form will show "Required" even after setting value this way
- **Fix**: Use `browser_type` (Hermes tool) or `locator.fill()` (Playwright) — these dispatch proper input/change events

### X Tweet Search Returns Nothing in Headless
- `x.com/search?q=from%3Ahandle&f=live` often returns 0 results even when tweets exist
- X's search index has a delay (minutes to hours for new accounts/posts)
- **Workaround**: Navigate directly to `x.com/handle/with_replies` to see all posts including replies

### New X Accounts Have Few/No Visible Posts
- Accounts created days ago may show "hasn't posted" or have 0 tweet elements in headless
- Posts might only be visible in non-headless mode or after longer wait times
- **Best effort**: Complete Follow + Form Submit (most important), skip Like/Quote/Tag if posts aren't found — note this for the user

### WL Form Submission Has No Explicit Success Message
- Most WL forms just close the modal on successful submit
- No "Success!", "Registered!", or confirmation toast
- **Indicator**: modal/form disappears = submission went through

### GraphQL API Is Unstable for X Actions
- Hard-coded queryIds (CreateFollow, FavoriteTweet, etc.) break when X deploys
- 404 "Query not found" is the error
- **Fix**: Use Playwright DOM clicks (more reliable) or scrape fresh queryIds from X's JS bundles

## Checklist Template

```
Airdrop: [PROJECT NAME]
URL: [registration URL]
X: @[project_handle]

Tasks:
- [ ] Follow @handle
- [ ] Like & Quote the post
- [ ] Tag 2 friends
- [ ] Submit EVM: [WALLET_ADDRESS]
- [ ] Submit X: @[your_handle]

Result:
- Follow: ✅/❌
- Like: ✅/❌
- Quote: ✅/❌
- Tag: ✅/❌
- Form Submit: ✅/❌
```
