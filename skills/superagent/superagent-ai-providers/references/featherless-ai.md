# Featherless.ai — LLM Model Hosting Platform

## Discovery (2026-07-13)

**Featherless.ai** is a model hosting platform discovered during EvoMap publish bottleneck troubleshooting. Not an alternative to EvoMap — it's a separate LLM provider with its own model catalog.

### Platform Profile

| Property | Value |
|----------|-------|
| **URL** | https://featherless.ai |
| **API** | https://api.featherless.ai |
| **Framework** | Nuxt SPA (Vue/Next.js) |
| **Turnstile** | Cloudflare Turnstile on `/login` |
| **Auth** | Email/password + register (not OAuth) |
| **Model count** | 42,900+ |
| **Pagination** | 1,071 pages (50 models/page) |
| **Filters** | Modality (Text/Vision/Embedding), Parameter size (7-9B to 1T), Model family (Qwen 3, Qwen 2, Llama, Mistral, Gemma, Kimi K2, GPT OSS) |

### Known Models (from `/models` page)

- `Qwen3-Embedding-8B` — 733 downloads, 2.3M views, Jun 2025
- `Qwen3-4B-Instruct-2507` — 893 downloads, 5.3M views, Aug 2025
- `NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` — 788 downloads, 1.1M views, Dec 2025
- `Qwen3-4B-Instruct` — various dates

### Model Row Format (HTML)

```html
<div class="model-row group relative flex w-full overflow-hidden rounded-lg border bg-background ...">
  <div class="flex ...">
    <span class="model-tag model-card-tag">Qwen</span>
    <span class="model-tag-warm">Warm</span>
    <span class="model-tag model-card-tag">8B</span>
    <span class="model-tag model-card-tag">32K</span>
  </div>
  <p title="Qwen/Qwen3-Embedding-8B">Qwen3-Embedding-8B</p>
  <div class="flex items-center gap-1.5 text-xs">
    <svg>733</svg> downloads
    <span>·</span>
    <svg>2.3M</svg> views
    <span>·</span> Jun 2025
  </div>
</div>
```

### Use for

- Alternative model hosting/search (similar to OpenRouter)
- Model discovery for new LLM providers
- Not a direct replacement for EvoMap — different platform, different credential system

### Notes

- VPS IP is NOT blocked by Featherless (works via direct curl)
- Requires unset `HTTP_PROXY/HTTPS_PROXY` env vars to avoid proxy interference
- No OAuth/API key found during initial scan — only email/password registration