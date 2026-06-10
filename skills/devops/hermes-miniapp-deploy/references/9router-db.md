# 9Router Database Reference

## Schema

### providerNodes
| Column | Type | Desc |
|--------|------|------|
| id | TEXT PK | UUID |
| type | TEXT | e.g. `openai-compatible` |
| name | TEXT | Display name |
| data | TEXT JSON | `{type, name, prefix, baseUrl, apiType}` |

### providerConnections
| Column | Type | Desc |
|--------|------|------|
| id | TEXT PK | UUID |
| provider | TEXT FK | → providerNodes.id |
| authType | TEXT | `api-key` |
| name | TEXT | e.g. `OpenRouter Primary` |
| priority | INTEGER | Lower = higher priority |
| isActive | INTEGER | 0 or 1 |
| data | TEXT JSON | `{apiKey, testStatus, lastError}` |

## Free Models (OpenRouter)
- `nex-agi/nex-n2-pro:free` — 262K ctx
- `qwen/qwen3-coder:free` — 1M ctx
- `nvidia/nemotron-3-ultra-550b:free` — 1M ctx
- `openai/gpt-oss-120b:free` — 128K ctx
- `moonshotai/kimi-k2.6:free` — 262K ctx

## Key Pitfall
Never put API keys directly in config.yaml — shell redacts them. Store in separate file (e.g. `~/.hermes/.or_key`) and read with `$(cat file)` or Python `open()`.
