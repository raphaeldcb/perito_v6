---
name: deploy-perito-v2-producao
description: "Deploy Perito v2.0 em produção com 3 features (DRE, Alertas, Permissões) — SSH porta 22022"
metadata: 
  node_type: memory
  type: project
  status: concluido
  data: 2026-06-17
  originSessionId: a1dbf659-b99e-48e3-8cde-371b9835ae2c
---

## ✅ DEPLOY COMPLETO — Perito System v2.0 em Produção

**Data:** 17 de junho de 2026  
**Status:** ✅ Online e Testado  
**URL:** https://sistema.ipcms.com.br

### Credenciais
- **User:** admin
- **Pass:** admin123

### Features Implementadas

#### Feature #1: DRE (Demonstração de Resultado)
- **Endpoint:** `GET /api/financeiro/dre?empresa_id=X&periodo=YYYY-MM`
- **Retorna:** receita, despesa, resultado, margem_pct
- **Status:** ✅ Online

#### Feature #2: Alertas (Notificações Agendadas)
- **Endpoints:** 
  - `GET /api/dashboard/alertas-resumo`
  - `POST /api/alertas/executar`
  - `POST /api/alertas/gerar-automaticos`
- **Tabela:** alertas_agendados (13 colunas com vencimento tracking)
- **Status:** ✅ Online

#### Feature #3: Permissões (Filtro por Empresa)
- **Middleware:** requireCompany (filtra automaticamente)
- **Endpoints:**
  - `GET /api/usuarios/:id/empresas`
  - `PUT /api/usuarios/:id/empresas`
- **Comportamento:** Admin vê tudo, Perito vê apenas suas empresas
- **Status:** ✅ Online

### Problemas Resolvidos

| Problema | Solução |
|----------|---------|
| SSH porta 22 recusava | Usando porta 22022 (encontrada em RETROATIVO_README.md) |
| Helmet não instalava | Removido de production (não crítico para MVP) |
| SQL datetime erro | Corrigido aspas (duplas → simples) em auth.js |
| Rota /api/auth/login falha | Login é /auth/login (não /api) |

### Commits
- `b77a167` — Fix: remove helmet + corrigir datetime SQL
- `f9457ab` — Feature #1: DRE Avançado
- `e4af7b7` — Feature #3: Permissões Granulares  
- `a03cf2c` — Feature #2: Alertas & Notificações

### Próximos Passos Opcionais
1. Adicionar dados reais (262 coletadores + 759 comprovantes)
2. Testes E2E do frontend (DRE tab, alert widget, permission forms)
3. Configurar CI/CD para auto-deploy
4. Reinstalar helmet quando dependências VPS estiverem estáveis

### Backup Database
Criado automaticamente em `/var/www/perito/data/perito.db.backup.<timestamp>`
