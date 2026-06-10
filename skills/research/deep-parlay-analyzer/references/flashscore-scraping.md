# Flashscore Browser Scraping — Live Score Extraction

## Problem
Clicking match links on Flashscore via `browser_click` often fails to navigate — the page stays on the listing. Direct URL navigation (`/pertandingan/team-a-team-b/`) also fails because the URL slug is not predictable.

## Working Solution
Use `browser_console` with JavaScript to extract scores directly from the listing page:

```javascript
// Extract all match scores from current view
(() => {
  const items = document.querySelectorAll('.event__match');
  const results = [];
  for (const item of items) {
    const t = item.textContent.trim().substring(0, 80);
    if (t.includes('Indo') || t.includes('Mozam') || t.includes('Mozambik')) {
      results.push(t);
    }
  }
  return JSON.stringify(results);
})()
```

### Output format (half-time):
`"Waktu ParuhIndonesiaMozambik10"` = HT, Indonesia 1-0 Mozambik
### Output format (full-time):
`"SelesaiIndonesia WKamboja W11"` = FT, Indonesia 1-1 Kamboja

## CSS Selectors
- `.event__match` — each match row
- `.event__time` — match status ("Waktu Paruh" = HT, "Selesai" = FT)
- Scores appear as numbers after team names in the text content

## Scrolling
If match not visible: `browser_scroll direction=down` (2-3x for friendlies section)

## Limitations
- Some scores behind login wall
- JS extraction only works after page fully loads
