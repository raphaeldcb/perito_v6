"""RAG Module — Vector search for semantic access to acervo (pgvector + embeddings).

Dois modos de indexação convivem na mesma tabela `documento_rag`:

1. **Push de embedding pronto** (`POST /indexar`, `POST /buscar`): usado pelo
   mac_agent para PDFs de autos — ele roda o Ollama local, gera o embedding e
   manda pronto; o backend só grava/compara. Sem dependência nova no backend.

2. **Indexação tabular server-side** (`GET /search`, `app/services/rag_indexer.py`,
   `scripts/rag_populate.py`): processos, intimações, laudos e financeiro são
   lidos direto do Postgres, viram texto e o PRÓPRIO backend chama o Ollama
   (`settings.ollama_url`) para gerar o embedding — usado para fundamentar
   prompts do Qwen (laudo, ofício etc) com contexto histórico real.
"""

from .router import router
from .schemas import Chunk, IndexarInput, BuscarInput

__all__ = [
    "router",
    "Chunk",
    "IndexarInput",
    "BuscarInput",
]
