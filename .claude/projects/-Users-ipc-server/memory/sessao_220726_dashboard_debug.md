---
name: sessao_220726_dashboard_debug
description: 22/07/26 Dashboard debug — 403 Forbidden mesmo com user logado
metadata: 
  node_type: memory
  type: project
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-22T22:34:27.493Z
---

# Dashboard 403 Forbidden Bug — 22/07/26

## Status
User vê dashboard mas stats/charts vazios. APIs retornam 403 (Forbidden).

## Facts Confirmed
- ✅ Backend APIs funcionam com token (curl teste OK)
  - `/api/v1/dashboard/stats` → 200 OK + dados reais
  - `/api/v1/processos` → 200 OK
  
- ✅ Frontend endpoint requer autenticação (`Depends(get_current_user)`)

- ✅ User ESTÁ logado (ProtectedRoute permite acesso)
  - Debug message "No token" NÃO apareceu
  - Significa localStorage.getItem('access_token') tem valor

- ❌ Frontend requisições retornam 403
  - Logs: `GET /api/v1/dashboard/stats HTTP/1.1" 403`
  - Significa: requisição chegou mas sem autenticação válida

## Root Cause Hypotheses
1. **Race condition**: requisições fazem ANTES de interceptor ser ligado
2. **Token inválido**: localStorage tem valor mas token expirou
3. **CORS**: browser bloqueando Authorization header
4. **Interceptor timing**: client.js interceptor não rodando antes de useEffect

## Next Steps (Fazer COM CALMA)
1. Adicionar console.log no Dashboard.jsx loadDashboard() pra ver se chama
2. Verificar se requisição tem Authorization header (via browser DevTools)
3. Verificar se token em localStorage é válido (fazer POST /auth/me)
4. Checar se interceptor.request está sendo executado
5. Possível: mudar useEffect pra executar DEPOIS de delay/garantir autenticação

## Files
- `/Users/ipc_server/projects/ipc-pericias-ai/v6/frontend/src/pages/Dashboard.jsx` — component
- `/Users/ipc_server/projects/ipc-pericias-ai/v6/frontend/src/api/client.js` — interceptor
- `/Users/ipc_server/projects/ipc-pericias-ai/v6/backend/app/routes/dashboard.py` — endpoint

## Why:** 20h+ luta — user pediu pra fazer direito, com calma, sem pressa
