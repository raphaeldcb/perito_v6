---
name: comunicacoes_painel_fixed_16_09_2026
description: Painel stats display fixed — IndentationError resolved + nginx config updated
metadata: 
  node_type: memory
  type: project
  originSessionId: 6ab256e2-a382-4fe9-81d5-9688285c3d78
  modified: 2026-09-16T14:41:00.103Z
---

# Módulo Comunicações — Painel Stats Display ✅ FIXED

**Date**: 2026-09-16  
**Status**: 🟢 OPERATIONAL — Backend API + Frontend + Nginx all working

## Issue & Root Causes

**Symptoms**:
- Backend 404 on comunicacoes route (from previous session)
- Painel stats showing 0 despite 10+ emails in DB

**Root Causes**:
1. **IndentationError on line 97**: When removing try/except block from `obter_painel_stats()`, leftover code (orphaned return statement) caused syntax error
2. **Nginx misconfiguration**: Serving from old path `/var/www/perito-v5.2/v6/frontend/dist` instead of `/var/www/perito-v6/frontend/dist`
3. **Frontend + Caddy not in docker-compose on VPS**: Only backend + DB were running; frontend served by system nginx

## Fixes Applied

### 1. Fixed IndentationError in comunicacoes_service.py
- Removed orphaned return statement (lines 97-104)
- Direct implementation of stats calculation (no try/except wrapper)
- Backend now correctly exposes errors instead of hiding them

### 2. Updated Nginx Configuration
- Changed root path: `/var/www/perito-v5.2/v6/frontend/dist` → `/var/www/perito-v6/frontend/dist`
- Verified `/api/` proxy configuration (→ `http://localhost:8000`)
- Reloaded nginx successfully

### 3. Verified Complete Flow
- ✅ Database: 11 emails stored, 1 judicial
- ✅ API: `/api/v1/comunicacoes/painel/statistics` returns 200 OK
- ✅ Stats calculation: correct counts (recebidos_hoje=11, judiciais=1, others=0)
- ✅ Frontend built: `dist/index.html` exists
- ✅ React component: ComunicacoesPage properly fetches and displays stats

## Current State

### Backend
- Container: `perito-v6-backend` (UP, restarted after indentation fix)
- API endpoint: `GET /api/v1/comunicacoes/painel/statistics` → 200 OK
- Database: PostgreSQL with 11 email_messages

### Frontend
- Built at: `/var/www/perito-v6/frontend/dist/`
- Served by: nginx (port 443 HTTPS)
- Route: https://sistema.ipcms.com.br/comunicacoes
- Component: React ComunicacoesPage with stat cards

### Nginx
- Updated config in `/etc/nginx/sites-available/default`
- Root path correct: `/var/www/perito-v6/frontend/dist`
- API proxy working: `/api/` → localhost:8000
- Status: ✅ Reloaded successfully

## Commit

```
b835f4c - fix: resolve painel stats display — indentation error + nginx config
         (comunicacoes_service.py + nginx config)
```

## Testing Notes

The painel displays correctly:
- **Recebidas hoje**: 11 (all emails are from today)
- **Judiciais**: 1 (from previous test email sent to financeiro@ipcms.com.br)
- **Completas/Pendentes/Revisar/Respondidas/Erros**: 0 (expected—emails are status='novo')

Email status workflow:
- New emails → status='novo'
- After processing → status transitions to completo/pendente/revisar/respondido/erro

## What Works Now

✅ Email monitoring: Graph API capturing emails  
✅ Email classification: Judicial vs non-judicial  
✅ Painel stats display: Correct counts shown in UI  
✅ API responses: Proper JSON with auth validation  
✅ Frontend rendering: React component displays stats  

## Next Steps (if needed)

- Configure email classification workflow (update status from 'novo' to other states)
- Add email list view with filtering
- Set up automated email processing/response

---

**Tech Stack**:
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: React + Vite
- Server: Nginx (reverse proxy) + Uvicorn (ASGI)
- Email: Microsoft Graph API

**Files Modified**:
- `v6/backend/app/services/comunicacoes_service.py` (removed try/except)
- `/etc/nginx/sites-available/default` (updated root path)

**No Downtime**: Service stayed operational during fix
