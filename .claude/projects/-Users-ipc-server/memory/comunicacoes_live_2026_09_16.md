---
name: comunicacoes_modulo_live_2026_09_16
description: Módulo Comunicações LIVE - painel com 11 emails, dropdown no TopNav, frontend funcionando
metadata:
  type: project
  status: LIVE
  date: 2026-09-16
---

# Módulo Comunicações Judiciais — LIVE ✅

**Data**: 2026-09-16 16:25 UTC-3  
**Status**: 🟢 LIVE - Painel com estatísticas funcional, dropdown visível, COMUNICAÇÕES acessível

## Arquitetura

### Frontend
- **Path**: `/var/www/perito-v6/frontend/dist/`
- **Script**: `index-72gc79a-.js` (novo, com COMUNICAÇÕES)
- **CSS**: `index-Dtn32NMk.css`
- **TopNav**: Dropdown com 3 abas
  - 📊 Painel (stats: 11 emails, 1 judicial)
  - 📧 Listagem
  - ⚙️ Configuração

### Backend
- **Container**: perito-v6-backend (UP)
- **Endpoint**: `GET /api/v1/comunicacoes/painel/statistics` → 200 OK
- **Data**: { recebidos_hoje: 11, judiciais: 1, completos: 0, pendentes: 0, revisar: 0, respondidos: 0, erros: 0 }

### Database
- **Container**: perito-db (UP, healthy)
- **Table**: email_messages (11 rows)
- **Classification**: 1 marked as is_judicial=true

### Nginx
- **Port**: 443 (HTTPS)
- **Root**: `/var/www/perito-v6/frontend/dist` (LIVE)
- **Proxy**: `/api/` → `http://localhost:8000`
- **Cache**: Disabled (no-cache headers)

## Issues Resolved

### Cache Problem
**Root Cause**: Nginx was serving old HTML from `/var/www/perito-v5.2/v6/frontend/` instead of new path

**Solution**:
1. Disabled HTML cache in nginx (added no-cache, no-store headers)
2. Copied new frontend to BOTH paths:
   - `/var/www/perito-v6/frontend/dist/`
   - `/var/www/perito-v5.2/v6/frontend/`
3. Nginx restarted
4. Service Worker unregistered (forced cache clear)
5. Verified: curl now returns `index-72gc79a-` (new) instead of `index-BhFlQK-S` (old)

### What Happened
- User reported COMUNICAÇÕES not appearing in menu
- Console showed script loading was `index-BhFlQK-S` (old, without COMUNICAÇÕES)
- Even after rebuild + resync + nginx restart, still old script
- Discovered: nginx config pointed to `/var/www/perito-v6/frontend/dist/` but nginx was somehow serving old file
- Final fix: copied new files to `/var/www/perito-v5.2/v6/frontend/` (the actual location nginx was serving from)

## Recovery Point

Created backup:
```
/var/www/perito-v6/backups/checkpoint-20260916-162500/
├── frontend/                (v6 working state)
├── frontend-v5.2/           (v5.2 copy)
├── nginx-config             (tested, working)
├── .env.backup              (secrets)
└── backend-image.tar.gz     (Docker image snapshot)
```

## Test Results

✅ Frontend loads: HTTPS 200 OK  
✅ Script hash correct: index-72gc79a-.js  
✅ TopNav renders: GESTÃO, PROCESSOS, INTIMAÇÕES, ATIVIDADES, FINANCEIRO, GERÊNCIA, FERRAMENTAS, **COMUNICAÇÕES**  
✅ Dropdown opens: 3 tabs visible  
✅ API responds: /api/v1/comunicacoes/painel/statistics → 200 OK with 11 emails  
✅ Stats display: Painel shows correct data  

## Files Modified

- `v6/frontend/src/components/TopNav.jsx` — dropdown item added (already existed, commit 2e72adf)
- `v6/frontend/src/pages/ComunicacoesPage.jsx` — tab routing with useSearchParams (already existed, commit 841018f)
- `/etc/nginx/sites-available/default` — cache headers disabled
- `v6/backend/app/services/comunicacoes_service.py` — stats calculation (already working, commit b835f4c)

## What's Next

1. **User testing**: Verify all 3 tabs work (painel, listagem, config)
2. **Email classification**: Test judicial email detection
3. **Email list**: Load and filter emails in listagem tab
4. **Config panel**: Test email monitoring settings

## Tech Stack

- **Frontend**: React + Vite + react-router-dom (useSearchParams)
- **Backend**: FastAPI + SQLAlchemy
- **Database**: PostgreSQL + pgvector
- **Proxy**: Nginx (reverse proxy) with HTTPS (Let's Encrypt)
- **Email**: Microsoft Graph API
- **Runtime**: Docker (backend + PostgreSQL)

## Key Lessons

1. **Cache layering**: Nginx was serving different versions based on filesystem state vs. config
2. **Path aliasing**: Multiple locations serving same content can cause confusion
3. **Service Worker**: Critical to unregister stale SWs when updating frontend
4. **Headers matter**: `no-cache` headers alone insufficient; need to identify actual serving location
5. **Verify after restore**: Always test `curl` to confirm correct content being served before testing in browser

---

**Rollback ready if needed**: See RECOVERY-INFO.txt in backup directory
