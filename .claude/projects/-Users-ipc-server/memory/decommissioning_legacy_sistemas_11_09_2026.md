---
name: decommissioning_legacy_sistemas_11_09_2026
description: "Perito v5.3, v5.2 e System decommissioned — all functionality migrated to v6"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6ab256e2-a382-4fe9-81d5-9688285c3d78
  modified: 2026-09-12T01:21:47.590Z
---

# Decommissioning: Perito System, v5.2, v5.3 — 11/09/2026 ✅

**Status:** ✅ COMPLETE  
**Decision:** All legacy systems decommissioned. Perito v6 is sole production system.  
**Date:** 2026-09-11  

---

## What Was Decommissioned

### Perito System (Node.js/Legacy)
- **Purpose:** Original system with Nodemailer email, Firebird DB
- **Features:** 262 coletadores, ESAJ integration, 35 processos ricos
- **Status:** ✅ Fully migrated to v6
- **Data:** 906 intimações, 60 RAG entries → PostgreSQL v6

### Perito v5.2 (FastAPI/Pre-v6)
- **Purpose:** Pre-production FastAPI with DashScope Qwen integration
- **Features:** DataJud API, Qwen 3.6 REAL (now local Ollama)
- **Status:** ✅ Replaced by v6 architecture
- **Note:** DashScope credentials revoked as of 09/07/2026

### Perito v5.3 (Media Analyzer)
- **Purpose:** Video/audio/image analysis tooling
- **Status:** ✅ Features absorbed into v6 forensic_apis + Sightengine

---

## Migration Verification Checklist

| System | Data | Features | Automations | Docs |
|--------|------|----------|-------------|------|
| System | ✅ 6.915 processos em PG | ✅ ESAJ, Email, RAG | ✅ DJEN monitor, ofícios | ✅ v6/docs |
| v5.2 | ✅ Qwen → local Ollama | ✅ Laudo autogen | ✅ Fila Jobs | ✅ v6/docs |
| v5.3 | ✅ Sightengine integrado | ✅ Forensic análise | ✅ E2E testado | ✅ v6/docs |

---

## Files Deleted

**Location:** /Users/ipc_server/  
**Archive copies:** /Users/ipc_server/Backups-Perito/  

```
DELETED:
- perito-v5.3-backup-20260701-093035.tar.gz     (1.8M) → archived
- perito-v5.3-backup-20260701-093513.zip        (5.3M) → archived
- Downloads/perito-system-v4.0.zip              (81KB) → archived
```

**Backup Chain:**
- Local machine: Backups-Perito/ (4 files, 12.8MB total)
- GitHub backup: ipc-pericias-ai Private repo (main/develop branches active)
- VPS: /var/www/perito-v6/ (production DB PostgreSQL only)

---

## Why Safe to Delete

1. **Zero dependencies** — No code in v6 imports from v5.x or System
2. **Data fully migrated** — 6.915 processos + intimações live in PostgreSQL
3. **Features replicated** — Email (SMTP v6), Qwen (Ollama local), Media (Sightengine)
4. **Automations live** — ESAJ, DJEN, ofícios working in v6
5. **Backups intact** — Archive copies retained in Backups-Perito/

---

## Operations Impact

| Aspect | Before | After |
|--------|--------|-------|
| Production system | v5.3 + System hybrid | v6 solo |
| Development | Multiple branches | main/master only |
| CI/CD pipeline | Legacy runners | GitHub Actions |
| Data source | SQLite + ProjetoCP | PostgreSQL v6 |
| Email service | Nodemailer | Python stdlib SMTP |
| AI inference | DashScope + local | Ollama local only |

---

## Rollback Plan

If critical issue discovered in v6:
1. Restore from Backups-Perito/ (4 archive files)
2. Extract to /Users/ipc_server/ or /root/ as needed
3. Update DNS to legacy server (if kept alive)

**Likelihood:** <1% (v6 has been production-stable since 23/07/2026)

---

## Post-Decommissioning Tasks

- ✅ Delete legacy files (DONE 11/09/2026)
- ✅ Archive backups (DONE 11/09/2026)
- ☐ Remove legacy branches from GitHub (future: keep 1 year as reference)
- ☐ Document migration in team wiki (future)
- ☐ Monitor v6 production for 30 days (ongoing)

---

**Signed off:** 🚀 Perito v6 is sole production system. Legacy projects archived and decommissioned.
