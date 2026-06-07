# Free LLM Provider Comparison (2026-06)

Providers offering free API access (OpenAI-compatible format preferred).
Test all endpoints with `curl -s --max-time 10 <base_url>/v1/models` before relying on them.

## Tier 1: Best Free Providers

### Cerebras (cloud.cerebras.ai) — 🥇 FASTEST
- **Speed**: ~2,000 tok/sec (fastest available)
- **Free tier**: 20 req/min, no credit card
- **Models**: llama-3.3-70b, llama-3.1-8b
- **API URL**: `https://api.cerebras.ai/v1`
- **Key format**: `csk-...`
- **Signup**: https://cloud.cerebras.ai
- **Note**: Uses proprietary CS-3 wafer-scale hardware. Insane throughput.

### Groq (groq.com) — 🥈 Fast + Generous Limits
- **Speed**: ~500 tok/sec
- **Free tier**: 14,400 req/day, 6,000 tokens/min, no credit card
- **Models**: llama-3.3-70b, mixtral-8x7b, gemma-2-9b, llama-3.1-8b
- **API URL**: `https://api.groq.com/openai/v1`
- **Key format**: `gsk_...`
- **Signup**: https://console.groq.com
- **Note**: LPU inference engine. Best free tier for volume.

### Google Gemini (aistudio.google.com) — 🥉 Strongest Models Free
- **Speed**: ~100 tok/sec
- **Free tier**: 15 RPM, 1M tokens/min, 1B tokens/billion/month, no credit card
- **Models**: gemini-2.5-pro, gemini-2.5-flash, gemma-4-27b
- **API URL**: `https://generativelanguage.googleapis.com/v1beta/openai` (OpenAI-compatible)
- **Key format**: `AIzaSy...`
- **Signup**: https://aistudio.google.com/apikey (instant, no form)
- **Note**: Can get key in 30 seconds. 1M context on pro model.

## Tier 2: Good Free Providers

### DeepSeek (platform.deepseek.com)
- **Speed**: ~80 tok/sec
- **Free**: 5M tokens bonus on signup ($10 credit equivalent)
- **Models**: deepseek-v3, deepseek-r1 (reasoning)
- **API URL**: `https://api.deepseek.com/v1`
- **Key format**: `sk-...`
- **Signup**: https://platform.deepseek.com

### SambaNova (sambanova.ai)
- **Speed**: ~500 tok/sec
- **Free**: Community tier, no credit card
- **Models**: llama-4-maverick-17b, deepseek-v3.2, gemma-4-31b, gpt-oss-120b
- **API URL**: `https://api.sambanova.ai/v1`
- **Key format**: varies
- **Signup**: https://cloud.sambanova.ai
- **Note**: 8 models listed, strong lineup with newest models.

### SiliconFlow (siliconflow.cn)
- **Speed**: ~150 tok/sec
- **Free**: 2,000 calls/day on signup
- **Models**: Qwen, DeepSeek, Llama, GLM (Chinese-focused)
- **API URL**: `https://api.siliconflow.cn/v1`
- **Key format**: `sk-...`
- **Signup**: https://cloud.siliconflow.cn
- **Note**: Best for Asian language models.

### Mistral (mistral.ai)
- **Speed**: ~100 tok/sec
- **Free**: Some models free tier
- **Models**: mistral-large, mistral-medium, codestral
- **API URL**: `https://api.mistral.ai/v1`
- **Key format**: varies
- **Signup**: https://console.mistral.ai

### Together AI (together.ai)
- **Speed**: ~200 tok/sec
- **Free**: $5 credit on signup
- **Models**: 200+ open source models
- **API URL**: `https://api.together.xyz/v1`
- **Key format**: varies
- **Signup**: https://api.together.xyz

## Tier 3: Already-Aggregated (No Separate Key Needed)

### OpenRouter Free Models (27 free, 346 total)
Accessible via existing OpenRouter key. Best free models by context length:
| Model | Context | Modality |
|-------|---------|----------|
| openrouter/owl-alpha | 1,048,756 | text |
| qwen/qwen3-coder:free | 1,048,576 | text |
| nvidia/nemotron-3-ultra-550b:free | 1,000,000 | text |
| nvidia/nemotron-3-super-120b:free | 1,000,000 | text |
| moonshotai/kimi-k2.6:free | 262,144 | text+image |
| google/gemma-4-31b-it:free | 262,144 | text+image+video |
| meta-llama/llama-3.3-70b-instruct:free | 131,072 | text |
| nousresearch/hermes-3-llama-3.1-405b:free | 131,072 | text |

### Cloudflare Workers AI (@cf/ prefix)
- 10 models free via FreeLLMAPI
- Included in current FreeLLMAPI setup (102 models total)

### OpenCode Free Proxy
- 6 free models including deepseek-v4-flash-free, mimo-v2.5-free
- Running on port 19912

## Adding Providers to FreeLLMAPI

```bash
# Add a new provider key
curl -s -X POST http://127.0.0.1:3001/api/keys \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"platform":"custom","key":"YOUR_KEY","label":"Groq Free","baseUrl":"https://api.groq.com/openai/v1"}'
```

Then add to Hermes custom_providers (see superagent-llm-proxy SKILL.md for the full pattern).

## Quick Priority for New Setup

1. **Cerebras** — fastest, 2 min signup, best for low-latency tasks
2. **Groq** — most generous free limits, best for volume
3. **Gemini** — instant key, strongest models, best for complex reasoning
4. **DeepSeek** — reasoning model (R1), good for analysis
5. **SambaNova** — newest models (Llama-4), good for cutting-edge
