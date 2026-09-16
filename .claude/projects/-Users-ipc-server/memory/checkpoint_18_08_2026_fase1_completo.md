---
name: checkpoint_18_08_2026_fase1_completo
description: Root Cause Investigation (Fase 1 Systematic Debugging) — 6 blockersidentificados + 1 fixado
metadata: 
  type: project
  originSessionId: 01d10b68-bc47-46e5-8c21-7c8325331d5d
  modified: 2026-08-18T17:17:23.080Z
---

# Checkpoint 18/08/2026 — Fase 1 Completo

## 🎉 BLOCKER FIXADO (1/6)

### ✅ BLOCKER 1: retry() backoff_factor — CORRIGIDO
**Arquivo:** `/app/utils.py` linha 12  
**Erro:** `TypeError: retry() got an unexpected keyword argument 'backoff_factor'`  
**Causa:** Parâmetro se chama `backoff`, não `backoff_factor`  
**Fix aplicado:** `sed -i 's/backoff_factor/backoff/g' /var/www/perito-v6/backend/app/utils.py`  
**Impacto:** Desbloqueou carregamento de 7 routers (intimacoes, fluxo_honorarios, inter_api, tjms, fake_detector, ferramentas)  

---

## 🔴 BLOCKERES PENDENTES (5/6)

### ❌ BLOCKER 2: Health Endpoint = 503 Service Unavailable
**Status:** 503  
**Componentes health:**
- ✅ db: ok
- ❌ qwen: error: Connection aborted RemoteDisconnected
- ✅ queue: ok
- ❌ redis: error: Connection refused localhost:6379
- ✅ circuit_breakers: all CLOSED

**Causa:** Qwen desconectado + Redis não rodando  
**Severidade:** 🟡 MÉDIO (sistema funciona, mas degradado)  

### ❌ BLOCKER 3: Apenas 4 Ferramentas Ativas (21 esperadas)
**Endpoint:** `GET /api/v1/ferramentas` = 200 OK  
**Retorna:** 4 ferramentas
```json
[
  "analisar" → Qwen 3.6 local,
  "midia" → Fake Media Detector,
  "pdf" → Conversor PDF,
  "esaj" → Busca ESAJ
]
```

**Faltam:** 17 ferramentas (calculadora, validador, extrator, etc)  
**Causa:** Não investigado ainda  
**Severidade:** 🔴 CRÍTICO (requisito era 17/21 integradas)  

### ❌ BLOCKER 4: Qwen Connection Aborted
**Erro:** `Connection aborted. RemoteDisconnected('Remote end closed connection without response')`  
**Verificado:** `curl http://localhost:11434/api/tags` = ✅ Qwen OK (local respondendo)  
**Causa:** Mismatch entre health check e status real (talvez health testa endpoint errado)  
**Severidade:** 🟠 ALTO (Qwen é crítico para IA)  

### ❌ BLOCKER 5: Redis Não Rodando
**Erro:** `Error 111 connecting to localhost:6379. Connection refused`  
**Status:** Container `perito-v6-worker` existe mas Redis NÃO é container separado  
**Causa:** Redis não está em rodando ou não está exposto em 6379  
**Severidade:** 🟡 MÉDIO (queue/jobs funcionam sem Redis, mas degradados)  

### ⚠️ BLOCKER 6: Pydantic dict_type Validation Errors
**Erro:** Alguns endpoints retornam validação inválida (nodes com inputs como list em vez de dict)  
**Exemplo:** `{'type': 'dict_type', 'input': ['protocola_esaj']}`  
**Causa:** Schema de response definido errado  
**Severidade:** 🟠 ALTO (respostas da API com erro formato)  

---

## Fase 1 Completa — Evidências Coletadas

| Componente | Status | Output | Criticidade |
|-----------|--------|--------|------------|
| Ferramentas count | ✅ 21 módulos | `ls -1 ... \| wc -l` = 21 | ✅ OK |
| Health endpoint | ⚠️ 503 degraded | `curl /health` = 503 | 🟠 ALTO |
| Qwen local | ✅ Respondendo | `curl localhost:11434/api/tags` = ✅ | ✅ OK |
| Database | ✅ 94 tabelas | `SELECT COUNT(*)` = ok | ✅ OK |
| Container backend | ✅ UP | `docker ps` = up 4h | ✅ OK |
| Alembic migrations | ❌ 0 migrations | Pasta vazia | 🟡 MÉDIO |
| pgvector extension | ❌ Não instalado | WARNING (não fatal) | 🟡 MÉDIO |
| Redis | ❌ Refused | localhost:6379 | 🟡 MÉDIO |

---

## Próximos Passos — Fase 2 (Pattern Analysis)

1. **BLOCKER 3:** Investigar por que 17 ferramentas não estão sendo carregadas
   - Check: rotas das ferramentas em `/ferramentas/*.py`
   - Check: arquivo de config/loader de ferramentas

2. **BLOCKER 2/4:** Fixar health endpoint
   - Investigar qual é o endpoint Qwen que health está testando
   - Talvez seja `localhost:11434` em vez de outro

3. **BLOCKER 5:** Redis (opcional, pode ser post-facto)
   - Adicionar Redis container se necessário
   - OU remover dependência Redis se não for crítica

4. **BLOCKER 6:** Pydantic validation (respostas estruturadas)
   - Encontrar schema inválido
   - Corrigir definição

---

## Anotações de Execução

- ✅ Systematic Debugging Fase 1 completa (18:20)
- ✅ Root cause trivial de retry() identificado e fixado
- ⏳ Fases 2-4 pending
- **Próxima sessão:** Continue com Fase 2 (Pattern Analysis) — enfoque BLOCKER 3 (ferramentas) e BLOCKER 2 (health/Qwen)

