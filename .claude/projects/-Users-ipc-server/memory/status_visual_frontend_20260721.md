---
name: status_visual_frontend_20260721
description: "Frontend visual melhorado — Plano de ação para merge + deploy 18h sem quebras"
metadata:
  type: project
  originSessionId: "live"
  modified: 2026-07-21T18:36:32.715Z
---

# Frontend Visual v6 — Plano de Execução 21/07/26

## 🎯 OBJETIVO

✅ Atualizar visual do Perito v6 (referência artifact)  
✅ **100% funcional** — sem quebras  
✅ Trabalho offline local  
✅ Deploy 18h no VPS (staging → prod)

---

## 📊 ESTADO ATUAL

### Frontend React (Vivo)
- **Path**: `/Users/ipc_server/projects/ipc-pericias-ai/v6/frontend/src/`
- **Status**: ✅ Funcional (routing, auth, components)
- **Pages**: Dashboard, Kanban, Processos, Ferramentas, Admin, etc (28 rotas)
- **Problema anterior**: Visual foi atualizado mas quebraram rotas/funcionalidade

### Visual Referência (Salvo)
- **Path**: `/Users/ipc_server/frontend/visual_referencia_20260721.html`
- **Conteúdo**: HTML puro (standalone) com CSS + mock JS
- **Formato**: Dashboard 4 abas (Dashboard/Kanban/Processos/Ferramentas)
- **Temas**: Light/Dark com CSS variables
- **Charts**: Chart.js (Receita/Especialidade/Conclusão/Status)

---

## 🔍 ANÁLISE CRÍTICA

### O Que o Visual Tem
✅ Header + Tab Navigation  
✅ Stats Cards (4 métricas)  
✅ Charts (4 gráficos)  
✅ Kanban Board (drag-drop)  
✅ Processos Table (search + pagination)  
✅ Modal Ferramentas (3 abas: ESAJ/Qwen/Ofício)  
✅ Theme Toggle (light/dark)

### O Que Precisa Ser Preservado
✅ Routing React (não usar HTML puro)  
✅ API calls ao backend (processosPage.jsx já faz)  
✅ Auth + ProtectedRoute  
✅ Componentes reutilizáveis  
✅ Store (Zustand)  

### O Risco (Por que quebrou antes)
❌ Substituir tudo por HTML puro (perde routing)  
❌ Deixar mock data ao invés de conectar API  
❌ Quebrar componentes existentes  
❌ Perder funcionalidade de páginas secundárias

---

## ✅ ESTRATÉGIA DE EXECUÇÃO

### FASE 1: Análise Offline (Agora)
- [ ] Ler estrutura do App.jsx + componentes principais
- [ ] Identificar CSS current + que muda
- [ ] Mapear dependências (Store, API, utils)
- [ ] Comparar visual novo vs estrutura React atual

### FASE 2: Implementação Modular (Offline)
- [ ] Atualizar `index.css` com novo design (CSS variables)
- [ ] Criar/atualizar componentes-chave:
  - `DashboardLayout.jsx` (header + tab navigation)
  - `StatsCard.jsx` (cards de métrica)
  - `ChartContainer.jsx` (wraps Chart.js)
  - `KanbanColumn.jsx` (drag-drop)
  - `ProcessosTable.jsx` (search + pagination)
  - `ToolsModal.jsx` (3 abas)
- [ ] Testar cada página (dev server local)

### FASE 3: Testes E2E Offline
- [ ] Login + Dashboard funciona
- [ ] Tabs mudam
- [ ] Charts renderizam
- [ ] Kanban drag-drop
- [ ] Processos table search + pagination
- [ ] Modais abrem/fecham
- [ ] Light/Dark theme funciona

### FASE 4: Deploy Staging (17h)
- [ ] Build frontend: `npm run build`
- [ ] SSH VPS + atualizar `/var/www/perito-v6/frontend/dist/`
- [ ] Verificar CORS, assets, 404s

### FASE 5: Deploy Produção (18h)
- [ ] Verificação final no site real
- [ ] Se quebrou algo: rollback imediato (backup já existe)

---

## 🛠️ PRÓXIMOS PASSOS CONCRETOS

### NOW (Este momento)
**Tarefas pra Qwen (pesado):**
1. Leia as 5 principais pages React (DashboardPage, KanbanPage, ProcessosPage, FerramentasPage)
2. Identifique a estrutura de cada (que componentes, que propsaça, que API calls)
3. Gere lista de arquivos a criar/atualizar

**Tarefas pra DeepSeek (verificação):**
4. Revise o visual HTML contra as pages React
5. Identifique gaps/conflitos (ex: modal não existe no React)
6. Sugira componentes novos vs atualização de existentes

**Tarefas pra Fable (arremate):**
7. Decida: qual é a abordagem mínima pra não quebrar nada?
8. Plano dia-a-dia de código

---

## ⏱️ CRONOGRAMA

| Hora | Task | Estimado |
|------|------|----------|
| 14:35 | Leitura das pages + análise Qwen | 15 min |
| 14:50 | Verificação DeepSeek | 10 min |
| 15:00 | Decision + Primeiro commit | 10 min |
| 15:10 | Atualizar CSS variables + componentes chave | 40 min |
| 15:50 | Testes dev server (todos pages) | 30 min |
| 16:20 | Refinamentos + fix de bugs | 40 min |
| 17:00 | **Build + Deploy Staging** | 20 min |
| 17:20-18:00 | QA staging + rollback contingency | 40 min |
| **18:00** | **DEPLOY PROD** (go/no-go) | 5 min |

**Total**: ~3 horas

---

## 🚨 ROLLBACK PLAN

Se algo quebrar em qualquer momento:
```bash
# VPS
cd /var/www/perito-v6
git log --oneline frontend/ | head -5
git revert <commit-hash>  # volta commit anterior
docker restart perito-v6-frontend
```

**Backup automático** já existe (DEPLOY.sh faz isso).

---

## 📝 COMMITS (Atomic)

```
1. "UI: Atualizar CSS variables + theme system"
2. "UI: Criar/atualizar componentes visuais (StatsCard, ChartContainer, KanbanColumn)"
3. "UI: Atualizar DashboardPage layout + responsive"
4. "UI: Implementar novo ToolsModal com 3 abas"
5. "UI: Atualizar ProcessosTable styling + search/pagination"
6. "UI: Testes visuais E2E — all pages passing"
```

Cada commit buildável + testável.

---

## ✅ CRITÉRIO DE SUCESSO

- ✅ Login → Dashboard (visual novo)
- ✅ Todos os tabs funcionam
- ✅ Charts renderizam corretamente
- ✅ Kanban drag-drop funciona
- ✅ Processos table search + pagination funciona
- ✅ Modais abrem/fecham sem erro
- ✅ Light/Dark theme muda tudo
- ✅ 0 console errors
- ✅ Responsive (mobile 768px funciona)
- ✅ Sem regressão em outras páginas (Admin, Ferramentas subareas, etc)

---

**Status**: 🟢 PRONTO PRA COMEÇAR  
**Mode**: ROUTERCLAUDE (Qwen pesado + DeepSeek check + Fable arremate)  
**Go time**: AGORA
