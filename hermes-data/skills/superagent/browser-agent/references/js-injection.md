# JS Injection Pattern — When UI Doesn't Render Results

## Problem

Some web apps (e.g., `dummylabs.live/cc-gen`) generate results client-side but don't render them to the DOM — they may download, copy to clipboard, or render in a canvas/WebGL element. Standard Playwright snapshots show empty pages.

## Solution Pattern

Use `browser_console` / `page.evaluate()` to run JavaScript directly in the page context:

```python
# Example: Generate Luhn-valid CC numbers via browser JS
js_code = """
function generateLuhn(prefix, length) {
  let digits = prefix.split('').map(Number);
  while (digits.length < length - 1) {
    digits.push(Math.floor(Math.random() * 10));
  }
  let sum = 0;
  for (let i = 0; i < digits.length; i++) {
    let d = digits[digits.length - 1 - i];
    if (i % 2 === 1) { d *= 2; if (d > 9) d -= 9; }
    sum += d;
  }
  digits.push((10 - (sum % 10)) % 10);
  return digits.join('');
}

const results = [];
for (let i = 0; i < 5; i++) results.push(generateLuhn('6233586370', 16));
JSON.stringify(results);
"""
```

## Debugging Empty Pages

When `browser_snapshot` returns empty:

1. **Check for modals/overlays** — press `Escape` to dismiss
2. **Check `document.body.innerText`** — may reveal hidden content
3. **Intercept network requests** — results may come via XHR/fetch, not DOM
4. **Check `console.log`** — intercept before triggering action
5. **Try `page.evaluate()`** — extract data directly from JS variables

## Intercept Pattern

```python
# Set interceptor BEFORE triggering the action
await page.evaluate("""
    window.__results = [];
    const origLog = console.log;
    console.log = function(...args) {
        window.__results.push(args.join(' '));
        origLog.apply(console, args);
    };
""")

# ... trigger the action ...

# ... read results
results = await page.evaluate("JSON.stringify(window.__results)")
```
