---
name: diagnostico-ia-routing-10-ago-2026
description: "Análise completa de roteamento de IAs no Perito v6 — situação atual, gaps, e integração OmniRoute"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8aab73fc-d030-46ed-a06a-e7a06873cba0
  modified: 2026-08-10T19:33:22.898Z
---

# 🔍 Diagnóstico: Roteamento de IAs & Balanceamento /free

**Data**: 10/08/2026  
**Status**: ⚠️ PARCIAL — Tem base, mas falta integração fallback  
**Prioridade**: ALTA — Necessário antes de modularização

---

## 📊 SITUAÇÃO ATUAL

### ✅ O que JÁ existe:

| Componente | Status | Detalhes |
|-----------|--------|----------|
| **Qwen Local (Ollama)** | ✅ ATIVO | Rodando em localhost:11434 (Perito) ou via OLLAMA_PROXY |
| **cerebro_intelligence.py** | ✅ ATIVO | Motor IA principal com análise de risco, RAG, decisões |
| **RAG + pgvector** | ✅ ATIVO | Busca semântica local (nomic-embed) em precedentes |
| **/free aliás** | ✅ ATIVO | Aliás `free` → `ccr code` (Claude Code Router) |
| **OmniRoute** | ✅ NOVO | Instalado 10/08, 427 modelos, localhost:20128 |
| **OLLAMA_PROXY** | ⚠️ PARCIAL | Config espera `http://localhost:20128` — COINCIDE COM OMNIROUTE! |

### ❌ O que FALTA:

| Gap | Impacto | Solução |
|-----|--------|---------|
| **Fallback lógica** | CRÍTICO | Qwen cai → sistema quebra. Precisa fallback automático |
| **Token monitor** | ALTO | Sem rastreamento de uso, não sabe quando fallback |
| **Load balance** | MÉDIO | Sem distribuição de carga entre provedores |
| **Retry policy** | MÉDIO | Sem retry automático em falhas |
| **Cost tracking** | BAIXO | Sem logging de qual IA foi usada (Qwen vs OmniRoute) |

---

## 🏗️ ARQUITETURA ATUAL

```
Claude Code /free Session
    ↓ (alias: free → ccr code)
[Qwen 3.14b local]
    ↓ (via OLLAMA_PROXY env var)
http://localhost:20128
    ↑
[OmniRoute] — 427 modelos gratuitos
    ↑
(Kiro, OpenCode, Pollinations, DeepSeek, Groq, etc)
```

### Pontos CRÍTICOS observados:

1. **OLLAMA_PROXY já aponta para :20128**
   - Arquivo: `backend/app/services/cerebro_intelligence.py:86`
   - Config: `self.qwen_host = qwen_host or os.getenv("OLLAMA_PROXY", "http://localhost:20128")`
   - ✅ **COINCIDÊNCIA PERFEITA**: Isso é EXATAMENTE a porta do OmniRoute!
   - ❌ **MAS**: Código NÃO diferencia Qwen vs OmniRoute — se Qwen falha, tudo falha

2. **Sem fallback lógica**
   - Linha 156: `resposta_qwen = await self._chamar_qwen(prompt, timeout=300)`
   - Se falhar → exception → request quebra
   - Sem retry automático em OmniRoute

3. **Sem token monitoring**
   - Não rastreia "quanto usamos desta IA"
   - Não sabe quando switchear para fallback
   - Sem logs de qual modelo foi usado (Qwen vs DeepSeek vs OpenCode)

---

## 🎯 PLANO MÍNIMO (1-2 dias)

### **Fase 0: Fallback Automático (URGENTE)**

Antes de qualquer modularização, PRECISA de:

```python
# backend/app/services/llm_router.py [NEW]
class LLMRouter:
    """Route requests: Qwen (local) → OmniRoute (free providers)"""
    
    async def call_llm(self, prompt: str, timeout=60) -> str:
        """
        Try sequence:
        1. Qwen local (fast, no cost)
        2. OmniRoute free fallback (Groq, DeepSeek, OpenCode)
        3. If both fail: raise with context
        """
        try:
            # Try local Qwen
            return await self._call_qwen(prompt, timeout)
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Qwen failed: {e}, falling back to OmniRoute")
            try:
                # Try OmniRoute free
                return await self._call_omniroute(prompt)
            except Exception as e2:
                logger.critical(f"Both Qwen and OmniRoute failed: {e}, {e2}")
                raise
    
    async def _call_qwen(self, prompt: str, timeout: int) -> str:
        """Local Qwen via OLLAMA_PROXY"""
        url = os.getenv("OLLAMA_PROXY", "http://localhost:20128")
        # POST to /api/generate (Ollama endpoint)
        response = await asyncio.wait_for(
            self._post_json(f"{url}/api/generate", {...}),
            timeout=timeout
        )
        return response["response"]
    
    async def _call_omniroute(self, prompt: str) -> str:
        """OmniRoute free providers (no auth needed for public)"""
        url = os.getenv("OMNIROUTE_URL", "http://localhost:20128")
        api_key = os.getenv("OMNIROUTE_API_KEY")
        
        # POST to OmniRoute /v1/chat/completions (OpenAI-compatible)
        response = await self._post_json(
            f"{url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            data={
                "model": "auto",  # Auto-select best free provider
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.7
            }
        )
        return response["choices"][0]["message"]["content"]
```

**Tarefas**:
1. Criar `backend/app/services/llm_router.py`
2. Modificar `cerebro_intelligence.py` para usar `LLMRouter`
3. Adicionar env vars: `OMNIROUTE_URL`, `OMNIROUTE_API_KEY`
4. Testes: mock Qwen falha → fallback OmniRoute funciona
5. Deploy em staging (homolog) antes de prod

### **Fase 1: Token Monitoring (1 dia)**

```python
# backend/app/services/token_monitor.py [NEW]
class TokenMonitor:
    """Track IA usage, detect when to prefer free providers"""
    
    async def log_usage(self, model: str, tokens_in: int, tokens_out: int, cost_usd: float):
        """Log which IA was used"""
        # Store in DB table: token_usage (timestamp, model, tokens, cost)
        pass
    
    async def should_use_free_provider(self) -> bool:
        """Check monthly budget, return True if should prefer free"""
        # Query: sum(cost_usd) from token_usage this month > threshold?
        pass
```

### **Fase 2: Load Balancing (optional, 1-2 dias)**

```python
# backend/app/services/provider_balancer.py [NEW]
class ProviderBalancer:
    """Distribute load across multiple free providers"""
    
    # Round-robin: Groq (fast) → DeepSeek (quality) → OpenCode (fallback)
    # If one provider hits rate limit, skip to next
```

---

## 💾 CONFIGURAÇÃO NECESSÁRIA

### `.env` (Perito v6)

```bash
# Existing (keep)
OLLAMA_PROXY=http://localhost:20128
OLLAMA_MODEL=perito-qwen

# NEW (add)
OMNIROUTE_URL=http://localhost:20128
OMNIROUTE_API_KEY=sk-omniroute-claude-code-free-1r4nd0mstr1ng123
OMNIROUTE_ENABLED=true

# Fallback strategy
LLM_ROUTER_TIMEOUT_QWEN=60
LLM_ROUTER_TIMEOUT_OMNIROUTE=30
LLM_ROUTER_MAX_RETRIES=2
LLM_ROUTER_PREFER_FREE=false  # true = prefer OmniRoute (save cost)
```

### `docker-compose.yml` (if modular)

```yaml
version: '3.8'

services:
  backend:
    environment:
      - OLLAMA_PROXY=http://ollama:11434  # Qwen service
      - OMNIROUTE_URL=http://omniroute:20128  # OmniRoute service
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
  
  omniroute:
    image: diegosouzapw/omniroute:latest
    ports:
      - "20128:20128"
    environment:
      - NODE_ENV=production
```

---

## 🧪 TESTES MÍNIMOS

```python
# backend/tests/test_llm_router.py

@pytest.mark.asyncio
async def test_qwen_fallback_to_omniroute():
    """Verify: Qwen down → OmniRoute used"""
    router = LLMRouter()
    
    # Mock Qwen to fail
    with patch("llm_router._call_qwen", side_effect=ConnectionError()):
        result = await router.call_llm("test prompt")
    
    # Should succeed via OmniRoute
    assert "response" in result

@pytest.mark.asyncio
async def test_both_fail_raises():
    """Verify: Both down → exception with context"""
    router = LLMRouter()
    
    with patch("llm_router._call_qwen", side_effect=ConnectionError()):
        with patch("llm_router._call_omniroute", side_effect=TimeoutError()):
            with pytest.raises(ProviderUnavailableError):
                await router.call_llm("test prompt")

@pytest.mark.asyncio
async def test_token_logging():
    """Verify: Usage logged correctly"""
    monitor = TokenMonitor()
    await monitor.log_usage("qwen", 100, 50, 0)
    await monitor.log_usage("deepseek", 200, 100, 0.01)
    
    usage = await monitor.get_monthly_usage()
    assert usage["total_tokens"] == 450
    assert usage["total_cost_usd"] == 0.01
```

---

## 📋 CHECKLIST PRÉ-MODULARIZAÇÃO

### Antes de começar modularização:

- [ ] **LLM Router implementado** (fallback automático)
  - [ ] Testes passam (Qwen → OmniRoute fallback)
  - [ ] Deploy em staging
  - [ ] Verificar em produção (health check verde)

- [ ] **Token Monitor ativo** (rastreamento de uso)
  - [ ] DB schema criado
  - [ ] Logging em tempo real
  - [ ] Dashboard de uso

- [ ] **OmniRoute configurado** em homolog/prod
  - [ ] API key gerada
  - [ ] Provedores conectados (Kiro, OpenCode, Pollinations)
  - [ ] Health check verde

- [ ] **Documentação atualizada**
  - [ ] `docs/architecture/LLM_ROUTING.md`
  - [ ] Runbook de fallback
  - [ ] Monitoramento de provedores

### DEPOIS disso, é seguro:

- ✅ Modularização backend
- ✅ Separação homolog/prod
- ✅ Refator frontend módulos

**Porque**: Com fallback automático, quebra de Qwen NÃO derruba sistema.

---

## 🎯 RECOMENDAÇÃO

**PARE A MODULARIZAÇÃO POR AGORA.**

Faça isso em ordem:

1. **Day 1**: Implementar LLM Router + testes
2. **Day 2**: Deploy em staging, validate
3. **Day 3**: Token Monitor + documentação
4. **Day 4-5**: DEPOIS aí sim, começar modularização (seguro agora)

**Por que?** Modularização sem fallback = risco desnecessário. Se Qwen quebra durante refactor, you're screwed. Com fallback = tranquilo, OmniRoute aguenta enquanto refatora.

---

## 📈 FUTURE (Post-Modularização)

```
Phase A (NOW): LLM Router fallback ✅
  ↓
Phase B (Later): Modular architecture
  ├─ Frontend modules
  ├─ Backend router modules
  └─ Entity modules
  ↓
Phase C (Future): Multi-provider orchestration
  ├─ Load balancer (distribute Qwen/Groq/DeepSeek)
  ├─ Cost optimizer (prefer cheapest per request)
  ├─ Quality scorer (track accuracy per provider)
  └─ SLA enforcer (latency/availability monitoring)
```

