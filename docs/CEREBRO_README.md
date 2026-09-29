# 🧠 Cérebro — Visual Workflow Builder

Sistema de automação visual integrado ao Perito v6. Permite criar, executar e monitorar workflows de perícia em tempo real.

## Visão Geral

| Componente | Status | Detalhe |
|-----------|--------|---------|
| **Backend** | ✅ Pronto | Models + Migration + Compilador + Endpoints |
| **Frontend** | ✅ Pronto | React Flow Canvas + Components |
| **Integration** | ✅ Pronto | API client + Routes |
| **Testes** | ⏳ Pendente | E2E com VPS (SQLite init error bloqueador) |

## Arquitetura

### Backend (Phase 1)

```
/api/v1/
├── workflow-nodes/types      GET: Introspect job types
├── workflows                 GET/POST/DELETE: CRUD
├── workflows/{id}            GET: Fetch definition
├── workflows/{id}/execute    POST: Trigger execution
└── workflows/{id}/executions/{exec_id}  GET: Poll status
```

**Modelos:**
- `WorkflowDefinition`: Stores nodes (JSONB), edges, triggers
- `WorkflowExecution`: Tracks runs with node_results

**Compilador:**
```python
WorkflowCompiler.compile(definition, trigger_id)
  → Validates DAG (no cycles)
  → Validates inputs (all satisfied)
  → Topological sort
  → Creates Job chain atomically
```

### Frontend (Phase 2+3)

**Pages:**
- `/cerebro`: Main canvas page

**Components:**
- `CerebroPage`: Canvas + Sidebar (tabs: editor, list, history)
- `WorkflowNode`: Drag-drop node with inputs
- `NodePalette`: Palette of available node types
- `WorkflowList`: Search + delete + clone
- `ExecutionHistory`: Replay + status
- `ErrorDisplay`: Modal for errors

**Features:**
- ✅ Drag-drop nodes
- ✅ Wire edges (node.output → node.input)
- ✅ Save workflows
- ✅ Execute with trigger_id
- ✅ Real-time monitoring (polling)
- ✅ Clone workflows
- ✅ Error handling (node-level)
- ✅ Replay execution

## E2E Testing Checklist

### 1️⃣ Setup
```bash
# Start VPS backend (fix SQLite init error first)
ssh -i ~/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186

# Verify migration applied
cd /var/www/perito-v6/backend
python3 -m alembic current  # Should show: 1784058523_workflows (head)

# Restart backend
pkill -f 'uvicorn app.main'
cd /var/www/perito-v6/backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Verify endpoints
curl http://localhost:8000/api/v1/workflow-nodes/types
```

### 2️⃣ Frontend Tests

**Test Case 1: Create Workflow**
1. Open `/cerebro` → Tab: "Editor"
2. See "Nós Disponíveis" palette (load from `/workflow-nodes/types`)
3. Drag "Gerar Laudo" node to canvas
4. Drag "Protocolo Ofício" node
5. Wire: gerar_laudo.output → protocolo_oficio.input (edge)
6. Click "💾 Salvar Workflow"
7. Enter name "Test Flow"
8. Expect: Workflow saved (ID returned, in list)

**Test Case 2: Execute Workflow**
1. Workflow from Test Case 1 selected
2. Click "▶️ Executar"
3. Prompt: Enter trigger_id (e.g., `123`)
4. Watch status panel:
   - Status: "running"
   - Nodes listed: gerar_laudo (processando), protocolo_oficio (na_fila)
5. Wait ~10 seconds (simulated execution)
6. Expect: Status → "completed" or "failed"

**Test Case 3: Workflow List**
1. Click "📋 Lista" tab
2. See search bar + workflow items
3. Search "Test" → filter results
4. Click item → selects workflow
5. Click "📋" (clone) → prompt for name
6. Click "🗑️" (delete) → confirm
7. Expect: List updates

**Test Case 4: Error Handling**
1. Create workflow with missing inputs
2. Execute with trigger_id
3. Watch monitoring
4. If node fails: Error modal appears
5. Show:
   - Node ID
   - Error message
   - Suggestion
6. Click "Fechar" → modal closes

**Test Case 5: Replay**
1. Go to "📊 Histórico" tab
2. See execution history (if implemented: list of past runs)
3. Click "🔁" (replay) on an execution
4. Expect: Re-run with same trigger_id

### 3️⃣ API Integration Tests

```bash
# 1. Get node types
curl -s http://localhost:8000/api/v1/workflow-nodes/types | jq .

# 2. Create workflow
curl -s -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Test",
    "nodes": [
      {
        "id": "node_1",
        "type": "gerar_laudo",
        "inputs": {"intimacao_id": "ref:trigger"}
      }
    ],
    "edges": []
  }' | jq .

# 3. Execute workflow (get ID from step 2)
curl -s -X POST http://localhost:8000/api/v1/workflows/1/execute \
  -H "Content-Type: application/json" \
  -d '{"trigger_id": 123}' | jq .

# 4. Poll execution
curl -s http://localhost:8000/api/v1/workflows/1/executions/1 | jq .
```

## Bloqueadores Conhecidos

### VPS SQLite Init Error
**Problema:** `init_db()` fails after 60s connection attempts
**Causa:** SQLite lock ou arquivo corrompido
**Solução:**
1. SSH para VPS
2. Verificar permissões: `ls -la /var/www/perito-v6/backend/data/perito_v6.db`
3. Se bloqueado: `rm /var/www/perito-v6/backend/data/perito_v6.db.lock 2>/dev/null`
4. Reiniciar backend
5. Se still fails: Check database file integrity (`sqlite3 ... ".tables"`)

### Backend Dependencies
- `slowapi` (rate limiting) — installed ✅
- `reportlab` (PDF generation) — installed ✅
- Check others: `pip install -r requirements.txt` on VPS

## Próximas Iterações (Phase 4+)

- [ ] Workflow execution history endpoint (GET /workflows/{id}/executions)
- [ ] Scheduled triggers (cron-based workflows)
- [ ] Webhook triggers (external event workflows)
- [ ] AI suggestion (Qwen recommends next node)
- [ ] Workflow templates (pre-built patterns)
- [ ] If/else branching (conditional nodes)
- [ ] RBAC per workflow (admin controls)
- [ ] Audit trail (who ran what)
- [ ] Workflow versioning

## How to Debug

**Frontend (React):**
```bash
cd /Users/ipc_server/projects/ipc-pericias-ai/v6/frontend
npm start  # Dev server on localhost:3000
```

**Backend (Python):**
```bash
cd /Users/ipc_server/projects/ipc-pericias-ai/v6/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Check Logs:**
```bash
# Mac agent
tail -f /tmp/backend.log

# VPS
ssh -p 22022 root@129.121.34.186 "tail -f /tmp/backend.log"
```

## References

- Spec: Phase 1 Backend + Phase 2 Frontend + Phase 3 Integration ✅
- Code: `/v6/backend/app/models/workflow.py`, `/v6/backend/app/routes/workflows.py`, `/v6/frontend/src/pages/CerebroPage.jsx`
- Migration: `20260716_add_workflow_tables.py` (SQLite compatible)
- Memory: `[[workflow-builder-cerebro]]` (detailed design notes)
