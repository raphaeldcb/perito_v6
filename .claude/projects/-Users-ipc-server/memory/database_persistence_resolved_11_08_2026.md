---
name: database_persistence_resolved_11_08_2026
description: "🎉 Database persistence DEFINITIVAMENTE resolvido — DROP SCHEMA bug eliminado, dados persistem após restart"
metadata: 
  node_type: memory
  type: project
  originSessionId: facbf296-2947-41f3-bc96-201ea9ae2b4d
  modified: 2026-08-11T15:11:13.316Z
---

# 11/08/2026 ✅ DATABASE PERSISTENCE — RESOLVIDO DEFINITIVAMENTE

## Problema Raiz Identificado
`init_db()` em `v6/backend/app/services/database.py:57` executava **`DROP SCHEMA IF EXISTS public CASCADE`** a **CADA startup**, destruindo todos os dados apesar de PostgreSQL estar configurado corretamente com named volumes (`perito-db-data`).

## Solução Implementada
**Fresh install detection**: Inspector verifica se tabelas já existem no banco:
- Se `len(existing_tables) == 0` → fresh install → executa DROP SCHEMA
- Se tabelas existem → restart → PULA DROP SCHEMA, preserva dados

Código (database.py:53-69):
```python
# Check if schema already has data (don't destroy it on restart)
try:
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    is_fresh_install = len(existing_tables) == 0

    if is_fresh_install:
        logger.info("🆕 Fresh install detected — creating schema")
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        logger.info("✅ Schema dropped and recreated")
    else:
        logger.info(f"♻️ Existing database detected ({len(existing_tables)} tables) — skipping DROP SCHEMA")
```

## Verificação E2E (11/08 12:10)
✅ **1,085 registros reais importados**:
- 188 processos (source_system='legado')
- 138 intimações (100% linkadas a processos)
- 506 receitas
- 253 despesas

✅ **Persistência verificada**: dados sobrevivem a `docker-compose down/up`

✅ **API funcional pós-restart**:
- POST /auth/login → 200 OK
- GET /processos?limit=5 → total: 188, retorna 5/página
- SELECT COUNT FROM processo → 188 ✓

✅ **Commit**: `aeab8ef` em `develop` + push remoto

## Status Produção
🟢 **SISTEMA 100% OPERACIONAL**
- Schema persistence: ✅
- API: ✅
- Database: ✅
- Login: ✅

Próximas fases: Algoritmos de análise forense + laudo automático
