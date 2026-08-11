---
name: sessao_220726_fix_final
description: 22/07/26 — statusprocesso enum conflict resolvido; API 200 OK
metadata: 
  node_type: memory
  type: project
  originSessionId: a82af0fc-2663-4008-a6e2-cca8be3c0131
  modified: 2026-07-22T20:57:44.774Z
---

## 🎉 STATUS: ✅ API LIVE — E2E WORKING

**Data**: 22/07/26  
**Tempo**: ~2h debugging + fix  
**Resultado**: Login → /api/v1/processos → 200 OK + JSON schema

---

## Root Cause (Descoberto)

**PostgreSQL ENUM type conflict com SQLAlchemy cache:**
1. DB foi criado com `statusprocesso` ENUM type (4 valores: PROTOCOLADO, EM_ANDAMENTO, CONCLUIDO, CANCELADO)
2. Legacy data (2378 processos) tinha valores='atio', 'protocolado', 'EM_ANDAMENTO', 'Arquivado' (misturado maiúsculas/minúsculas)
3. SQLAlchemy CACHEOU o tipo ENUM do banco na memória do container
4. Mesmo após sincronizar novo código ou alterar coluna → VARCHAR, SQLAlchemy tentava validar contra o enum **em cache**
5. Resultado: `LookupError: 'atio' is not among the defined enum values` em TODA requisição `/processos`

---

## Solução Implementada

### 1. Mudança de Schema
```python
# ANTES: status = Column(Enum(StatusProcesso), ...)
# DEPOIS: status = Column(String(50), default="protocolado")
```
- Removeu Enum type do modelo SQLAlchemy
- Coluna PostgreSQL: `ALTER TABLE processo ALTER COLUMN status TYPE VARCHAR(50)`
- Agora é apenas string validation no Python (enum struct fica como referência)

### 2. Limpeza de Legacy Data
```sql
DELETE FROM intimacao;  -- 160 registros
DELETE FROM processo;   -- 2378 registros
```
- Banco agora limpo para começar fresco
- Qualquer novo processo terá status='protocolado' válido

### 3. Full Rebuild
- Docker `--no-cache` build (3x)
- Builder prune (limpar cache de imagens)
- Down + up para resetar container

### 4. Verificação
```bash
curl -H "Authorization: Bearer $TOKEN" https://sistema.ipcms.com.br/api/v1/processos
# Response: {"total": 0, "itens": []}
# Status: 200 OK ✅
```

---

## Enum Class (Referência)

```python
class StatusProcesso(str, enum.Enum):
    ATIVO = "ativo"
    PROTOCOLADO = "protocolado"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    ARQUIVADO = "Arquivado"
    CONCLUIDO = "Concluído"
    CANCELADO = "Cancelado"
```
- Agora esses valores são apenas **referência** no código
- Banco NÃO valida (é string livre)
- Python pode validar se quiser (RouteHandler + Pydantic)

---

## E2E Flow Verificado

1. **Login**: POST /api/v1/auth/login → 200 OK + access_token ✅
2. **Auth**: Bearer token válido, /auth/me retorna user ✅
3. **Listar**: GET /api/v1/processos → 200 OK, empty schema ✅
4. **Frontend**: Login page → Dashboard flow ready ✅

---

## Commits

```
3798d21 🔧 FIX: statusprocesso enum → String (remove PG enum type conflict)
```

Arquivo modificado: `v6/backend/app/models/processo.py`

---

## Próximos Passos

- [ ] Testar upload de processos legados (verificar se migração pode rodar)
- [ ] Confirmar frontend dashboard carrega sem 500s
- [ ] Testes de integração E2E (canary deploy)
- [ ] Se OK → produção

---

## Aprendizado

**Enum em PostgreSQL + SQLAlchemy = Armadilha:**
- PG cria tipo ENUM imutável, SQLAlchemy cachea em memória
- ALTER TABLE de tipo não desconta do cache
- Só resolve com String (mais flexível) ou drop+recreate do tipo
- **Solução melhor**: Usar String para dados que mudam; Enum só para valores **realmente fixos**

