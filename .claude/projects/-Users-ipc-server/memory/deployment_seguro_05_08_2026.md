---
name: deployment_seguro_strategy
description: Estratégia de deployment seguro para mudanças no backend sem quebrar sistema vivo
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7c467360-9d68-48a8-88e5-e9d96cc8cf87
  modified: 2026-08-05T15:17:30.702Z
---

## Estratégia de Deployment Seguro

**Data**: 05/08/2026  
**Problema resolvido**: Sistema quebrava toda vez que tentava adicionar features (forensic laudo)

### A Solução: `safe_deploy.sh`

Script com 4 fases:

1. **TESTE LOCAL** — verifica syntax + imports ANTES de tocar no VPS
2. **BACKUP VPS** — cria snapshot compactado em `/tmp/` do estado anterior
3. **SYNC SEGURO** — rsync das mudanças (exclui .env, __pycache__)
4. **RESTART + TESTE CRÍTICO** — reinicia container e verifica:
   - `/health` endpoint
   - `/api/v1/processos` (rota mais crítica)
   - Se falhar, rollback automático

### Implementação do Forensic Laudo (Corretamente)

**Sem quebrar nada existente:**
- Modelos isolados em `backend/app/models/forensic.py` (novo arquivo)
  - `LaudoForense` (não conflita com `Laudo` existente)
  - `ClienteForense` (não conflita com nenhum modelo de cliente)
  - `MidiaOrigem` (novo enum)
  - `StatusPagamento` (novo enum)
- Tabelas separadas: `laudos_forense` (não `laudo` que já existe)
- Imports no `__init__.py` adicionados DEPOIS do laudo.py original

**Resultado:**
- ✅ Models importam OK
- ✅ Zero conflito de naming
- ✅ Safe_deploy.sh passou
- ✅ Backend online (sem quebra de processos)

### Problema Encontrado no Deploy

`.env` do VPS tinha variáveis obsoletas:
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GEMINI_API_KEY`
- `STRIPE_API_KEY`
- `STRIPE_WEBHOOK_SECRET`

Pydantic Settings 2.5 bloqueia "extra inputs" por padrão → backend não iniciava.

**Fix:**
```bash
grep -v "GOOGLE_APPLICATION_CREDENTIALS\|GEMINI\|STRIPE" .env > .env.new && mv .env.new .env
```

### Próximas Features

Use **SEMPRE** esse padrão:

1. Criar modelos em arquivo separado (ex: `models/forensic.py`)
2. Adicionar imports ao `__init__.py`
3. Rodar `safe_deploy.sh` (vai testar + fazer rollback automático)
4. Se passar → commit + push automático
5. Se falhar → reverte e mostra o erro

Nunca mais "oq deveria ter atualizado também não" — apenas o que foi pedido muda.

### Comando para Deploy Futuro

```bash
bash v6/scripts/safe_deploy.sh
```

Se passar: ✅  
Se falhar: ❌ + rollback automático + log de erro

---

**Why:** Sistema vivo em produção. Zero downtime é lei. Rodar testes ANTES de tocar.

**How to apply:** Toda vez que adicionar feature ao backend, rodar safe_deploy.sh antes de confiar que funcionou.
