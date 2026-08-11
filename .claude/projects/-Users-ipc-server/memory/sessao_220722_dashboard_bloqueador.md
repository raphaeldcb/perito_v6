---
name: sessao_220722_dashboard_bloqueador
description: 22/07/26 — Dashboard 403 FIXADO, mas UI dados não renderizam (bloqueia entrega)
metadata:
  type: project
  status: BLOQUEADO
  progresso: 95%
---

# Dashboard — Bloqueador Final 22/07/26

## ✅ RESOLVIDO (Fase 1-2)

### 403 Forbidden — ROOT CAUSE
- **Problema**: Frontend requisições retornavam 403 apesar de user logado
- **Causa**: Race condition — Dashboard.jsx fazias requisições ANTES de `authStore.init()` completar
- **FIX**: Adicionar `initialized` à dependency array de useEffect + Zustand seletores corrigidos
- **Commits**: ed12ba1, a16a129, 8247ffb, etc

### Zustand Seletores — CORRIGIDO
```javascript
// ❌ ERRADO: perdia reatividade
const { user, initialized } = useAuthStore()

// ✅ CORRETO: mantém reatividade
const user = useAuthStore(s => s.user)
const initialized = useAuthStore(s => s.initialized)
```
- Aplicado em: Dashboard.jsx, ProtectedRoute.jsx, PublicRoute.jsx

### Backend APIs — 100% FUNCIONANDO ✅
- `/api/v1/dashboard/stats` → 200 OK com dados reais
- `/api/v1/dashboard/receita-mes` → dados corretos
- `/api/v1/dashboard/volume-especialidade` → dados corretos
- `/api/v1/dashboard/status-distribuicao` → dados corretos
- Verificado via curl com Bearer token

---

## 🔴 BLOQUEADOR — UI Renderização

### O Problema
Dashboard.jsx renderiza layout completo MAS stat cards mostram "--" em vez de valores reais.

Evidências:
1. **Backend funciona**: curl com token → 200 OK + dados reais ✅
2. **Frontend autenticação funciona**: ProtectedRoute permite acesso ✅
3. **Layout renderiza**: Sidebar, filters, charts containers aparecem ✅
4. **Dados NÃO aparecem**: Stat cards mostram "--" sempre ❌
5. **Mesmo hardcoded não funciona**: Initial state `{ meus_processos: 999 }` → ainda "--" ❌
6. **Fetch direto testado**: Removido axios, testado com fetch() puro → ainda "--" ❌

### Debugging Feito
- ✅ Verificou CORS headers (corretos)
- ✅ Verificou token em localStorage (presente)
- ✅ Verificou /auth/me call (200 OK)
- ✅ Verificou client.js interceptor (correto)
- ✅ Adicionou logging em authStore.init(), App.jsx, Dashboard.jsx
- ✅ Testou sem check de initialized → ainda não funciona
- ✅ Testou com hardcoded initial state → não renderiza
- ✅ Testou com fetch direto → não funciona
- ✅ Modificou StatCard para sempre render string → não funciona

### Hipóteses Não Testadas (Sem Acesso ao Console)
1. **React render bug**: Componente tem erro JS que impede render
2. **CSS escondendo**: Display:none ou overflow:hidden nos valores
3. **Recharts bug**: Charts DOM está ocupando espaço onde stats estariam
4. **Zustand timing**: State update não dispara re-render (pouco provável, testado com seletores)
5. **Component tree**: StatCard não é chamado (unlikely, layout renderiza)

---

## 🚀 Próximos Passos (Para Bruno ou Próxima Sessão)

### Imediato
1. Abrir navegador no Mac com Dev Tools (F12)
2. Fazer login em sistema.ipcms.com.br
3. Verificar console.logs:
   - `[Dashboard RENDER]` → mostra `dashboard` state
   - `[StatCard]` → mostra valores passados ao component
   - `[loadDashboard]` → mostra se requisição rodou
4. Verificar React DevTools:
   - Inspeccionar `<Dashboard>` component
   - Checar `dashboard` state value
   - Checar se setDashboard foi chamado

### Investigação
Se console logs NÃO aparecem:
- loadDashboard() não está sendo chamada → verificar por que useEffect não roda

Se console logs APARECEM com dados corretos:
- StatCard recebe valor correto MAS não renderiza → verificar HTML/CSS do stat-value div

### Solução Provável
Adicionar a linha ANTES do return em Dashboard.jsx:
```javascript
if (dashboard?.meus_processos === undefined) {
  return <div>Loading... (initialized={initialized})</div>
}
```
Isso vai mostrar se dashboard é null ou se há outro issue.

---

## Arquivos Modificados (22/07/26)

**Frontend:**
- v6/frontend/src/pages/Dashboard.jsx (múltiplas iterações)
- v6/frontend/src/components/ProtectedRoute.jsx
- v6/frontend/src/components/PublicRoute.jsx
- v6/frontend/src/store/authStore.js
- v6/frontend/src/App.jsx

**Backend:** (OK, nenhuma mudança necessária)

**Git Status:**
```
692576d CLEAN: Remove hardcoded initial state, volta a null
df62093 DEBUG: Console.log no StatCard
b31f713 FIX: StatCard sempre renderiza string, nunca null
56519a7 TEST: Hardcoded fallback data
9761f41 TEST: Hardcoded initial state
...14 commits anteriores...
```

---

## Aprendizados

1. **Zustand + React**: Desestruturação sem seletores PERDE reatividade
2. **Race Conditions**: Cuidado com async init() em useEffect dependencies
3. **Debugging sem Dev Tools**: Muito difícil — adicione logging agressivamente
4. **CSS pode esconder dados**: Sempre verificar visibility/display/overflow

---

## Status Final

**Sistema**: 95% pronto para produção
**Bloqueador**: Renderização de dados no Dashboard (UI issue, não backend)
**Time Estimate**: 30-60 min se tiver acesso ao console do navegador
**Recomendação**: Pause, debug com Dev Tools abertos, depois continue

