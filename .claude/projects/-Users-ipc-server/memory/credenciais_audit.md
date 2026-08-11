---
name: credenciais_audit
description: "Auditoria COMPLETA de credenciais VPS — locais, formatos, como acessar"
metadata: 
  node_type: memory
  type: reference
  session: 20260714
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# 🔐 AUDITORIA DE CREDENCIAIS — VPS 129.121.34.186

**REGRA:** Antes de procurar qualquer coisa no VPS, ler este documento primeiro.

---

## 1. SSH ACCESS

| Item | Valor | Local |
|------|-------|-------|
| Host | root@129.121.34.186 | VPS produção |
| Port | 22022 | SSH remoto |
| Key | `~/.ssh/id_ed25519_perito` | Mac |
| Type | Ed25519 | Segura, moderna |

```bash
ssh -i ~/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186
```

---

## 2. ENV VARIABLES — ONDE ESTÃO

**NÃO estão em um único .env centralizado.**

Estão espalhados em:

| Location | Usage | Access |
|----------|-------|--------|
| `/var/www/perito-v6/backend/.env` | Backend VPS FastAPI | SSH + cat |
| Docker container ENV | Backend + Workers | `docker inspect <container>` |
| Ollama (Mac) | OLLAMA_MODEL=perito-qwen | ~/.zshrc or runtime |
| Mac agent | PERITO_API_URL, AGENT_API_KEY | environment |
| Windows agent | PERITO_API_URL, AGENT_API_KEY | PowerShell $env: |

---

## 3. DATABASE CREDENTIALS

### v6 (Current)
- **File:** `/var/www/perito-v6/backend/data/perito_v6.db`
- **Type:** SQLite (Docker volume `v6_perito_storage:/data`)
- **Access:** Via `docker exec perito-v6-backend python3` (NO sqlite3 binary in container)
- **State:** EMPTY (not yet migrated from v4/v5)

### v5/v4 (Legacy — HAS DATA)
- **File:** `/var/www/perito/data/perito.db`
- **Type:** SQLite
- **Access:** Direct via `python3 -c "import sqlite3..."`
- **Contains:** 828+ processes, intimações, histórico
- **⚠️ NOTE:** Backup daily in `/var/www/perito/data/backups/` (latest: perito_2026-07-14.db)

### PostgreSQL (? unused)
- **Not found in current setup** — probably v2/v3 legacy
- If needed: check `docker ps` for postgres container

---

## 4. GRAPH API / OFFICE 365 / AZURE

**STATUS:** CREDENTIALS CONFIGURED BUT NOT ACCESSIBLE NOW

Location: `/var/www/perito-v6/backend/app/services/graph_mail.py`

```python
TENANT_ID = os.environ.get("GRAPH_TENANT_ID", "")
CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GRAPH_CLIENT_SECRET", "")
MAILBOX = os.environ.get("GRAPH_MAILBOX", "ipcms@ipcms.com.br")
```

**WHERE ARE THEY SET?**
- ❌ NOT in `/var/www/perito-v6/backend/.env` (checked 2026-07-14)
- ❌ NOT in Docker container env (checked 2026-07-14)
- ⚠️ **LIKELY:** Set in deployment config or manually via `docker run -e` at startup
- ❌ **CURRENT STATUS:** NOT WORKING (Graph API returns empty response)

**ACTION NEEDED:** 
1. Ask Bruno where these were set during deployment
2. Store in secure location
3. Add to `credenciais_vps.env` (create!)

---

## 5. EMAIL ACCESS

### adm@ipcms.com.br
- **Type:** Office 365 mailbox
- **Access:** Via Graph API (above)
- **Purpose:** Monitor intimations from TJMT emails
- **Current:** Graph API broken → cannot fetch emails automatically

**FALLBACK:** Direct email client access (Outlook web)

---

## 6. ONEDRIVE / SHAREPOINT

### Location
Path: `C:\Users\{bruno}\OneDrive - Bibliotecas Compartilhadas\IPCMS - ARQUIVOS\PROCESSOS\intimações baixadas`

### Access
- **Local (Windows):** Direct file copy (pjewin.py uses this)
- **Programmatic:** Graph API (same as email creds above)

### Credentials
- Same as GRAPH_* env vars above

---

## 7. DOCKER NETWORK

| Item | Value |
|------|-------|
| Network Name | `v6_perito-network` |
| Backend Container | `perito-v6-backend` (port 8000 internal) |
| Frontend Container | `perito-v6-frontend` (nginx, port 80/443) |
| Database Volume | `v6_perito_storage:/data` |
| Worker Container | `perito-v6-worker` |
| DB Container | `perito-v6-db` (postgres? unused?) |

**Access inside container:** `http://perito-v6-backend:8000`
**Access from host:** `http://localhost:8000` or `http://129.121.34.186:8000`

---

## 8. URLS & ENDPOINTS

| Service | URL | Auth |
|---------|-----|------|
| Perito Dashboard | https://sistema.ipcms.com.br | JWT (browser login) |
| Backend API | http://129.121.34.186:8000 | X-Agent-Key OR JWT |
| Agent Key | `perito-mac-agent-key-v6-2026-07-14` | Set 2026-07-14 in .env |
| Ollama (Mac) | http://127.0.0.1:11434 | None (local) |

---

## 9. API KEYS / TOKENS

| Service | Key Name | Status | Notes |
|---------|----------|--------|-------|
| DashScope (Qwen) | DASHSCOPE_API_KEY | ❌ REVOKED (2026-07-09) | Qwen now via Ollama local |
| DataJud (CNJ) | PUBLIC (no key) | ✅ Working | Rate-limited |
| CNPJ (ViaCEP) | PUBLIC | ✅ Working | Free tier |
| Ollama Token | None (local) | ✅ Working | Mac-only |

---

## 10. TODO — CENTRALIZE

### Create: `/tmp/credenciais_vps.env`

```bash
# Azure / Office 365
GRAPH_TENANT_ID=???
GRAPH_CLIENT_ID=???
GRAPH_CLIENT_SECRET=???
GRAPH_MAILBOX=adm@ipcms.com.br

# Agent Keys
AGENT_API_KEY=perito-mac-agent-key-v6-2026-07-14

# Database
PERITO_DB_PATH=/var/www/perito-v6/backend/data/perito_v6.db
PERITO_DB_LEGACY=/var/www/perito/data/perito.db

# OneDrive
ONEDRIVE_INTIMACOES_PATH=C:\Users\bruno\OneDrive - Bibliotecas Compartilhadas\IPCMS - ARQUIVOS\PROCESSOS\intimações baixadas

# API Endpoints
PERITO_API_URL=http://129.121.34.186:8000
OLLAMA_URL=http://127.0.0.1:11434
```

---

## 11. HOW TO QUERY DATABASE GOING FORWARD

**Always use this pattern (NO sqlite3 binary in Docker):**

```bash
docker exec perito-v6-backend python3 -c "
import sqlite3
db = sqlite3.connect('/app/data/perito_v6.db')
# ... your query
"
```

Or for legacy DB:

```bash
ssh -i ~/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186 "python3 -c \"
import sqlite3
db = sqlite3.connect('/var/www/perito/data/perito.db')
# ... your query
\""
```

---

## 12. STATUS SUMMARY

| System | Configured | Working | Notes |
|--------|-----------|---------|-------|
| SSH Access | ✅ | ✅ | Ed25519 key on Mac |
| FastAPI Backend | ✅ | ✅ | Docker, port 8000 |
| Frontend (Nginx) | ✅ | ⚠️ | Returns 502 sometimes (backend network) |
| Database v6 | ✅ | ✅ | Empty, ready for migration |
| Database v5/v4 | ✅ | ✅ | Has real data (828 processes) |
| Graph API | ✅ Config | ❌ | Credentials location unknown, API broken |
| OneDrive | ✅ | ✅ | Windows only, local sync |
| Ollama (Mac) | ✅ | ✅ | Qwen 3.6 local, no internet needed |
| Email Monitoring | ❌ | ❌ | Needs Graph API fix |

---

## 13. NEXT ACTIONS

1. ✅ **Document this** (DONE — you're reading it)
2. ⏳ **Find Graph API creds** — ask Bruno where set during deployment
3. ⏳ **Create centralized credenciais file** — `/tmp/credenciais_vps.env`
4. ⏳ **Fix Graph API** — restore email monitoring
5. ⏳ **Extract real TJMT CNJs** — from `/var/www/perito/data/perito.db`

---

**Last updated:** 2026-07-14 14:00 UTC
**Created by:** Claude Code (in response to Bruno's feedback)
**To update this:** Always check here first before grep/find on VPS
