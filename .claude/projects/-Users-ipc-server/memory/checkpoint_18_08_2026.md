---
name: checkpoint_18_08_2026_todos_pendentes
description: Plano executivo 18/08/2026 — requisitos vs integração vs correções urgentes
metadata: 
  node_type: memory
  type: project
  originSessionId: 01d10b68-bc47-46e5-8c21-7c8325331d5d
  modified: 2026-08-18T14:51:11.870Z
---

# Checkpoint 18/08/2026 — TODOS Pendentes

## Status Verificado
- ✅ Containers UP (backend 2h, db 4d)
- ✅ Ferramentas módulos existem: `/var/www/perito-v6/backend/app/modules/ferramentas`
- ❌ Swagger `/docs` = 404
- ❌ Saúde sistema não confirmada

## Requisitos Pendentes (O QUE FOI PEDIDO)

### Backend
- [ ] Health endpoint funcional (qual é o real?)
- [ ] Todas 17 ferramentas integradas e respondendo
- [ ] Endpoints `/api/v1/ferramentas/*` testados
- [ ] Erros de rotas documentados

### Frontend
- [ ] Ferramentas dashboard carregando
- [ ] Botão de cada ferramenta funcional
- [ ] Integração com backend OK (HTTP 200)

### Integração Qwen/Ollama
- [ ] Fallback automático quando Claude enche quota
- [ ] 9router/OmniRoute configurado no dashboard
- [ ] Health check Qwen: `curl http://localhost:11434/api/tags`

### Database
- [ ] Validar 1.085+ registros persistidos (último checkpoint 11/08)
- [ ] Índices existem
- [ ] Backups rodam 00:00 daily

## Ações Imediatas (RUNNER SCRIPT para `/free`)

```bash
#!/bin/bash
# Diagnóstico + Correção Rápida

echo "=== FERRAMENTAS ==="
ssh -p 22022 root@129.121.34.186 "ls -1 /var/www/perito-v6/backend/app/modules/ferramentas | wc -l"

echo "=== HEALTH REAL ==="
ssh -p 22022 root@129.121.34.186 "grep -r '@app.get.*health' /var/www/perito-v6/backend/app/ 2>/dev/null | head -3"

echo "=== QWEN ALIVE? ==="
curl -s http://localhost:11434/api/tags 2>&1 | grep -q "perito-qwen" && echo "✅ Qwen OK" || echo "❌ Qwen DOWN"

echo "=== TESTES DB ==="
ssh -p 22022 root@129.121.34.186 "docker exec perito-db psql -U perito -d perito_v6 -c 'SELECT COUNT(*) as total_registros FROM processos;' 2>&1"

echo "=== ÚLTIMOS ERROS ==="
ssh -p 22022 root@129.121.34.186 "docker logs perito-v6-backend 2>&1 | grep -i error | tail -5"
```

## Próxima Sessão Via `/free`
1. Rodar script acima
2. Coletar 5 outputs
3. Classificar por criticidade (blocker/alto/médio)
4. Corrigir 1 blocker por ciclo (TDD)
5. Revalidar (curl/test)

---

**Anotação:** Token limit 18/08 15h30 — parado em diagnóstico. Retomado com `/free`.
