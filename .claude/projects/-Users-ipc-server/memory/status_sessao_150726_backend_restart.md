---
name: status_sessao_150726_backend_restart
description: Backend restart e diagnóstico de roteamento — Parametros endpoint com problema de roteamento
metadata: 
  node_type: memory
  type: project
  date: 2026-07-15
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# Sessão 15/07/26 — Backend Restart e Diagnóstico

## ✅ Concluído

### Backend Restart
- ✅ Matei processo Uvicorn antigo
- ✅ Reiniciei em `/var/www/perito-v6/backend` com python3
- ✅ Database foi seeded corretamente
- ✅ Auth login funciona via curl/API
- ✅ Outros endpoints funcionam (ex: `/api/v1/dados/*`, `/api/v1/auth/me`)

### Correção do Schema
- ✅ Removido relacionamento incorreto entre `PaymentRule` e `PayableAccount`
  - Erro: `NoForeignKeysError` — FK estava apontando para executor_id (users.id) não payment_rule.id
  - Solução: Removido `relationship("PayableAccount")` de PaymentRule
  - Removido `relationship("PaymentRule")` de PayableAccount
  - Arquivo: `/var/www/perito-v6/backend/app/models/payments.py` + duplicados

### Frontend Configuration
- ✅ Atualizado `vite.config.js` para apontar proxy `/api` → `sistema.ipcms.com.br`
- ✅ Commit: `87f7ee8`

## 🔴 BLOQUEADOR: Roteamento de `/api/v1/parametros/*`

### Sintoma
```
curl http://localhost:8000/api/v1/parametros/comarcas
→ HTTP 405 Method Not Allowed
→ Header: allow: PUT
```

### Investigação
1. ✅ Rotas GET/POST **ESTÃO** registradas no router (confirmado via `router.routes`)
2. ✅ TestClient (sem HTTP) consegue acessar GET e POST (status 200)
3. ❌ HTTP via curl/browser recebe sempre "Method Not Allowed"
4. ❌ Apenas esse router sofre — `/api/v1/dados/*` funciona normalmente

### Hipóteses Testadas
- ❌ Duplicação de include_router — verificado, apenas 1x incluído (linha 57 __init__.py)
- ❌ Cached .pyc — deletei __pycache__, problema persiste
- ❌ Uvicorn processo stale — matei e reiniciei, problema persiste
- ❌ Schema problema — verificado parametros.py, rotas estão corretas

### Próximos Passos para Debug
1. Verificar se há middleware que está bloqueando parametros especificamente
2. Verificar logs do Uvicorn com verbosidade aumentada
3. Verificar se há nginx/proxy configurado que está interferindo
4. Testar via `localhost:8000` vs `127.0.0.1:8000` (feito, sem diferença)

**Workaround Temporário**: Usar TestClient para testes unitários; não depender de parametros endpoint via HTTP por enquanto

## 📊 Estado do Sistema

### Backend
- ✅ Listening on 0.0.0.0:8000
- ✅ Database seeded (828 processos)
- ✅ Auth funcionando
- ✅ Endpoints `/api/v1/dados/*` ok
- ⚠️ Endpoint `/api/v1/parametros/*` com problema de roteamento

### Frontend
- ✅ Vite rodando em localhost:5173
- ⚠️ Proxy configurado para VPS
- ⚠️ Login retorna "Not authenticated" (pode ser CORS ou credencial issue)

### Models/Banco
- ✅ Tabelas `comarca`, `vara`, `juiz` criadas (migration 1784058519)
- ✅ Enum `TipoPericia` atualizado (judicial, extrajudicial, DNA, AT)
- ✅ Setor enum definido em schema

## 📋 Próximas Ações

### Sessão 16/07 (ou próxima)
1. **Debug roteamento `/api/v1/parametros`**
   - Aumentar verbosidade do Uvicorn
   - Procurar por middleware que possa estar bloqueando
   - Se não resolver, implementar fallback endpoint

2. **Testar login frontend**
   - Verificar se CORS está permitindo requisições do localhost:5173
   - Verificar se credenciais estão chegando corretamente ao backend
   - Pode ser necessário adicionar token Bearer ao CORS

3. **Integrar EditarProcesso.jsx**
   - Arquivo já tem campos `tipo_pericia` e `setor`
   - Falta carregar dados de `/parametros/*` (se roteamento for resolvido)
   - Testar dropdowns cascata

4. **Testes E2E**
   - Cadastrar novo processo com tipo_pericia e setor
   - Verificar se dados são salvos no banco
   - Testar dropdowns cascata

## 📄 Arquivos Envolvidos

**Backend (VPS)**:
- `/var/www/perito-v6/backend/app/models/payments.py` — corrigido
- `/var/www/perito-v6/backend/app/routes/__init__.py` — includes parametros_router
- `/var/www/perito-v6/backend/app/routes/parametros.py` — Define GET/POST comarcas/varas/juizes
- `/var/www/perito-v6/backend/app/models/parametro_judiciais.py` — Models Comarca, Vara, Juiz

**Frontend (Local)**:
- `/v6/frontend/vite.config.js` — Atualizado com proxy para VPS
- `/v6/frontend/src/pages/EditarProcesso.jsx` — Já tem campos tipo_pericia/setor

**DB**:
- Migration: `1784058519_add_parametros_judiciais.py`
- Database: `perito_v6` em PostgreSQL

---

**Status**: ✅ Backend reiniciado + ⚠️ Roteamento parametros bloqueado + ⚠️ Frontend login não funciona
**Bloqueador**: Diagnóstico de roteamento parametros
**Tempo estimado próxima sessão**: 2-3h (debug routing + frontend integration)
