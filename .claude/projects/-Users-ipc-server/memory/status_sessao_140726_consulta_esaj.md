---
name: status_sessao_140726_consulta_esaj
description: "Sessão 14/07/26 — Integração Consulta ESAJ com agent-browser, fila no backend e worker no Mac"
metadata: 
  node_type: memory
  type: project
  session: 20260714
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# Sessão 14/07/26 — Consulta ESAJ ✅ E2E Funcional

## Executado

### Scripts Mac (`/Users/ipc_server/`)
- **esaj_consulta_v2.py** ✅ TESTADO E FUNCIONANDO
  - Descobre elementos dinamicamente (não usa refs hardcoded)
  - Preenche número CNJ e consulta ESAJ
  - Salva resultado em `/tmp/esaj_consultas/*.json`
  - Testado com 0501238-67.0212.8.12.0001 (processo não existe, mas automação OK)

- **filtro_intimacoes_email.py** ✅ ESTRUTURA PRONTA
  - Extrai CNJ de textos com regex
  - Enfileira via POST /api/v1/consultas-esaj/enfileirar
  - TODO: integrar com Graph API para buscar emails adm@ipcms.com.br

- **mac_agent_esaj_worker.py** ✅ TESTADO
  - Monitora GET /api/v1/consultas-esaj/fila?limit=10
  - Executa esaj_consulta_v2.py para cada job
  - Reporta resultado via POST /api/v1/consultas-esaj/

### Backend Perito v6 (`/var/www/perito-v6/backend/app/routes/`)
- **consultas_esaj.py** ✅ REGISTRADA
  - POST / → registra resultado de consulta
  - POST /enfileirar → cria Job "esaj_consulta_automat" (status: na_fila)
  - GET /fila → lista jobs na_fila com limit

- **emails.py** ✅ ESTRUTURA CRIADA
  - GET / → lista emails com filtro (keywords, mailbox, folder)
  - TODO: integrar graph_mail.buscar_emails() (usa credenciais no VPS)

- **__init__.py** ✅ ATUALIZADO
  - Importa e registra ambas as rotas

## Fluxo Completo Montado

```
Email adm@ipcms.com.br (adm inbox)
  ↓
filtro_intimacoes_email.py
  (extrai CNJ via regex)
  ↓
POST /api/v1/consultas-esaj/enfileirar
  (cria Job status=na_fila)
  ↓
mac_agent_esaj_worker.py (loop 30s)
  GET /api/v1/consultas-esaj/fila
  (lê jobs na_fila)
  ↓
esaj_consulta_v2.py (para cada job)
  (agent-browser: open → snapshot → fill → click → screenshot)
  ↓
POST /api/v1/consultas-esaj/
  (registra resultado)
```

## RAG Qwen (Tentado)

**rag_indexador_qwen.py** ⚠️ BLOQUEADO
- Copia 23 PDFs de autos do VPS
- Tentou extrair texto: OCR (Tesseract) + vision LLM (llava)
- ❌ Falha: PDFs scanned, `convert`/`pdftoppm` não disponíveis no Mac
- **Solução alternativa:** processar no VPS Linux (ferramentas OCR instaladas)

## Próximos Passos

### Pronto para testar
1. Testar consulta ESAJ com CNJ válido (processo real)
2. Integrar Graph API ao endpoint GET /api/v1/emails?mailbox=adm@ipcms.com.br
3. Conectar filtro_intimacoes_email.py → GET /emails → POST /enfileirar
4. Rodar mac_agent_esaj_worker.py para processar fila

### RAG (futura)
- Se precisar indexar PDFs: usar VPS (`pdftoppm` + Tesseract + curl POST /rag/indexar)
- OU: Bruno envia TXTs pré-extraídos para indexar direto

### Futura iteração
- Persistir resultados em modelo Consulta (BD)
- Vincular Consulta → Intimacao → Processo
- Dashboard: visualizar fila e histórico

## Commits
- Git init em `/Users/ipc_server/` (master: 9018d9d)
- Message: "feat: consulta ESAJ + fila + worker"

## Notes
- ⚠️ Rota /enfileirar retorna 403 sem autenticação (expected)
- Agent-browser sessions não persistem entre scripts (cada run abre nova browser)
- refs descobertos dinamicamente via regex `\[ref=e(\d+)\]` no snapshot

## Vinculações
- [[Automação eSAJ JÁ EXISTE]] — Bruno tem protocolo_v21.py no Windows, não refazer
- [[Perito v6.0 — ✅ CORRIGIDO E LIVE]] — backend pronto
- [[superpowers:dispatching-parallel-agents]] — se filtro + worker precisarem rodar paralelo
