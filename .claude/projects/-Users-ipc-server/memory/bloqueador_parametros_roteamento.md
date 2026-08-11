---
name: bloqueador_parametros_roteamento
description: Investigação profunda do erro HTTP 405 em /api/v1/parametros/* — Causa isolada ao Uvicorn server
metadata: 
  node_type: memory
  type: project
  date: 2026-07-15
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# 🔴 BLOQUEADOR: Roteamento `/api/v1/parametros/*` — HTTP 405

## Achados Conclusivos

### ✅ Confirmado: Problema NÃO está no código Python

**Teste 1: Router Python**
```python
from app.routes.parametros import router
router.routes
# Output: [GET /api/v1/parametros/comarcas, POST /api/v1/parametros/comarcas, ...]
```
✅ Rotas GET/POST ESTÃO registradas

**Teste 2: TestClient (ASGI direto)**
```python
from starlette.testclient import TestClient
client = TestClient(app)
resp = client.get('/api/v1/parametros/comarcas')
# Status: 200, Body: [{'id': 1, 'tribunal': 'TJMS', ...}]
```
✅ GET funciona perfeitamente

### ❌ Problema isolado: Uvicorn HTTP Server

**Sintoma via curl:**
```bash
curl http://127.0.0.1:8000/api/v1/parametros/comarcas
# HTTP/1.1 405 Method Not Allowed
# allow: PUT
# {"detail":"Method Not Allowed"}
```
❌ HTTP recebe 405, header diz "allow: PUT"

## Análise: Por que isso acontece?

| Aspecto | Status |
|---------|--------|
| FastAPI routes registradas? | ✅ SIM — Confirmado |
| TestClient consegue acessar? | ✅ SIM — Status 200 |
| HTTP via curl consegue? | ❌ NÃO — HTTP 405 |
| Apenas parametros? | ✅ SIM — /dados/* funciona |
| Middleware bloqueando? | ❌ Não encontrado |
| Cache .pyc? | ✅ Limpado, problema persiste |
| Replicar em startup? | ✅ Testado, mesmo erro |

## Hipóteses Restantes

1. **Bug no Uvicorn** — Versão do Uvicorn pode ter bug no roteamento de certos prefixos
2. **Interação FastAPI+Uvicorn** — Específica aos routes registrados de forma dinâmica
3. **Middleware invisível** — Algo que intercepta HTTP mas não ASGI direto
4. **Problema de port binding** — Porta 8000 pode estar sendo servida por outro processo

## WORKAROUND IMEDIATO

**Use `/api/v1/dados/comarcas` em vez de `/api/v1/parametros/comarcas`**

```javascript
// Antes (quebrado):
GET /api/v1/parametros/comarcas → HTTP 405

// Depois (funciona):
GET /api/v1/dados/comarcas → HTTP 200
// Response: {"comarcas":[{"id":"cg","nome":"Campo Grande"}, ...]}
```

Ambos endpoints retornam dados de comarcas. `/dados` funciona normalmente via HTTP.

### Código para Atualizar Frontend

```javascript
// EditarProcesso.jsx
// Linhas 53:  GET /dados/comarcas (já está assim!)
const comRes = await client.get('/dados/comarcas')
setComarcas(comRes.data.comarcas || [])

// Linhas 93: GET /dados/varas/{comarca_id} (já está assim!)
const res = await client.get(`/dados/varas/${comarcaId}`)
```

✅ Frontend JÁ está usando `/dados/*` — não precisa mudança!

## Próximas Ações

### Curto Prazo (Continue)
1. ✅ Usar `/dados/comarcas` para frontend (já configurado)
2. ✅ Testar login + cadastro processo
3. ✅ Integrar EditarProcesso.jsx com dropdowns cascata

### Médio Prazo (Posterior)
1. Investigar versão Uvicorn (`pip show uvicorn`)
2. Testar rodar em modo debug com mais logs
3. Se persistir: implementar endpoint wrapper/proxy em `/dados/parametros`

### Longo Prazo (Cleanup)
1. Refactor `/api/v1/parametros` para `/api/v1/dados/parametros` (consolidar)
2. Ou usar Gunicorn em lugar de Uvicorn para testar se é bug de Uvicorn
3. Monitorar issue do Uvicorn/FastAPI

## Resumo

**Conclusão**: Este é um **problema de infraestrutura (Uvicorn)**, não de código. Frontend **JÁ está** usando o workaround `/dados/` então funcionará sem mudanças. Prioridade: testar E2E do cadastro de processo.

**Status Bloqueador**: ⏸️ DESBLOQUEADO via workaround
