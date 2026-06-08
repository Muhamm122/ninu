# FreeLLMAPI Key Management

## Adding API Keys (Direct SQLite Insert)

FreeLLMAPI stores API keys encrypted (AES-256-GCM) in SQLite DB. Encryption key auto-generated in `settings` table.

### Location
- **DB**: `/opt/freellmapi/server/data/freeapi.db`
- **App root**: `/opt/freellmapi/server/`

### Insert Keys via Node.js
```bash
cd /opt/freellmapi/server
node --input-type=module -e '
import crypto from "crypto";
import Database from "better-sqlite3";
import dotenv from "dotenv";
dotenv.config({ path: "/opt/freellmapi/.env" });
const ALGO = "aes-256-gcm";
const db = new Database("/opt/freellmapi/server/data/freeapi.db");
let encKey = process.env.ENCRYPTION_KEY;
if (!encKey) {
    const row = db.prepare("SELECT value FROM settings WHERE key = ?").get("encryption_key");
    encKey = row ? row.value : crypto.randomBytes(32).toString("hex");
}
const kb = Buffer.from(encKey, "hex");
function enc(text) {
    const iv = crypto.randomBytes(16);
    const c = crypto.createCipheriv(ALGO, kb, iv);
    const e = c.update(text, "utf8", "hex") + c.final("hex");
    return { e, iv: iv.toString("hex"), at: c.getAuthTag().toString("hex") };
}
const now = new Date().toISOString().replace("T"," ").slice(0,19);
const nk = enc("YOUR_KEY_HERE");
db.prepare("INSERT INTO api_keys (platform,label,encrypted_key,iv,auth_tag,status,enabled,created_at) VALUES (?,?,?,?,?,?,?,?)")
  .run("nvidia","nvidia-direct",nk.e,nk.iv,nk.at,"unknown",1,now);
'
```

### Provider Key Sources
| Platform | URL | Free |
|----------|-----|------|
| OpenRouter | https://openrouter.ai/keys | Limited |
| NVIDIA NIM | https://build.nvidia.com | Yes |
| Google AI | https://aistudio.google.com/app/apikey | 15 req/min |
| Groq | https://console.groq.com/keys | 30 req/min |
| HuggingFace | https://huggingface.co/settings/tokens | Limited |
| Cloudflare | https://dash.cloudflare.com/profile/api-tokens | Workers AI |

### Version Check
```bash
cat /opt/freellmapi/server/package.json | grep version
curl -s https://raw.githubusercontent.com/tashfeenahmed/freellmapi/main/server/package.json | grep version
curl -s https://api.github.com/repos/tashfeenahmed/freellmapi/commits/main | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['sha'][:8], d['commit']['author']['date'])"
```

### Fallback Chain (Built-in)
- MAX_RETRIES=20, cooldown per model+key, penalty decay every 2min, key round-robin, sticky sessions

### Pitfalls
- execute_code blocks subprocess — use terminal/curl for crypto ops
- Quote nesting in terminal — use write_file + curl -d @file
- Keys show "unknown" until health checker runs
