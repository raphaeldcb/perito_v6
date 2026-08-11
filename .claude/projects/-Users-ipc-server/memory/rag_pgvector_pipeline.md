---
name: rag-pgvector-pipeline
description: "RAG semântico no Perito v6 — pgvector + embeddings locais (nomic), rota ponytail escolhida em vez do Dify"
metadata: 
  node_type: memory
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# RAG semântico (pgvector) — LIVE 09/07/26, commit 5d287cc

Escolhida a **rota ponytail** em vez do Dify (8 containers): RAG mínimo embutido no
stack existente. Busca precedentes/trechos do acervo para fundamentar laudos e reduz
token no Qwen (só trechos relevantes vão ao prompt, não o PDF inteiro).

**Arquitetura:**
- DB: trocado `postgres:15-alpine` → `pgvector/pgvector:pg15` (mesmo PG15, dados
  preservados no volume) + `CREATE EXTENSION vector`.
- `backend/app/routes/rag.py`: tabela `documento_rag` (origem, ref_id, chunk_idx,
  texto, `embedding vector(768)`, índice HNSW cosine). SEM dep nova — vetor gravado
  via literal `::vector`. Endpoints (JWT): `POST /rag/indexar`, `POST /rag/buscar`,
  `GET /rag/stats`.
- Embeddings: **nomic-embed-text (768d)** no Ollama local do Mac. O mac_agent gera;
  o backend só armazena/busca (cosine `<=>`).
- `scripts/mac_agent.py`: `_embed`, `_chunk`, job `indexar_rag`, `_recuperar_contexto`
  injeta trechos no prompt de `gerar_laudo`.
- `jobs.py`: todo laudo gerado auto-enfileira `indexar_rag` → o acervo cresce sozinho.

**Testado E2E:** busca "atualizar dívida em execução c/ juros" rankeou o laudo
contábil (0.712) acima de engenharia/médico. ✓

**Próximo (opcional):** indexar o acervo real de laudos (OneDrive/MODELOS) via jobs
`indexar_rag` em lote para o RAG ter massa de precedentes.

Relacionado: [[perito-qwen-modelo]] (gera o laudo), [[apis_publicas_integradas]].
