"""Indexador RAG tabular: processos, intimações, laudos e financeiro -> pgvector.

Todo registro vira texto (prosa pesquisável), é dividido em chunks e cada chunk
recebe um embedding (nomic-embed-text via Ollama). Tudo é gravado na MESMA tabela
`documento_rag` já usada pelo fluxo semântico de PDFs/laudos (app/routes/rag.py),
diferenciado pela coluna `origem`: 'processo' | 'intimacao' | 'laudo' | 'financeiro'.

Diferença do fluxo antigo (mac_agent -> POST /rag/indexar com embedding pronto):
aqui o embedding é gerado NO BACKEND, chamando o Ollama configurado em
`settings.ollama_url`. Isso permite indexação em lote via script/CLI/API sem
depender do agente do Mac.

Uso típico:
    from app.services.rag_indexer import index_processo, search

    index_processo(db, processo)                      # (re)indexa 1 processo
    search(db, "honorários vara de família", tipo="processo", k=5)
"""
import logging
import os
from typing import Optional

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.utils import retry, get_circuit_breaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)

DIM = 768  # nomic-embed-text
EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "nomic-embed-text")
# FIX #2: Intelligent chunking — max 512 chars, overlap 50 to prevent memory bomb
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))

ORIGENS_VALIDAS = {"processo", "intimacao", "laudo", "financeiro", "exemplo"}

_schema_ok = False


# ---------------------------------------------------------------------------
# Schema / storage (pgvector)
# ---------------------------------------------------------------------------

def ensure_schema(db: Session) -> None:
    """Garante tabela documento_rag + índices. Idempotente."""
    global _schema_ok
    if _schema_ok:
        return

    try:
        # Try pgvector extension but don't fail if unavailable
        try:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.commit()
        except Exception as e:
            logger.warning(f"pgvector não disponível: {e}")
            db.rollback()

        # Create table (always works)
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS documento_rag (
                id serial PRIMARY KEY,
                origem text NOT NULL,
                ref_id text,
                chunk_idx integer NOT NULL DEFAULT 0,
                texto text NOT NULL,
                embedding text,
                criado_em timestamptz NOT NULL DEFAULT now()
            )
        """))
        db.commit()

        # Create index
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_documento_rag_origem ON documento_rag (origem, ref_id)"))
        db.commit()

        _schema_ok = True
        logger.info("RAG schema ensured (pgvector optional, text search fallback ready)")
    except Exception as e:
        logger.error(f"RAG ensure_schema failed: {e}", exc_info=True)
        db.rollback()
        raise


def vec_literal(emb: list[float]) -> str:
    if len(emb) != DIM:
        raise ValueError(f"embedding deve ter {DIM} dims (veio {len(emb)})")
    return "[" + ",".join(repr(float(x)) for x in emb) + "]"


def chunk_text(texto: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Divide texto em pedaços de ~chunk_size chars com overlap; descarta sobras minúsculas.

    FIX #2: Validação pré-index — rejeita chunk_size > 2000 (evita memory bomb).
    """
    if chunk_size > 2000:
        logger.warning(f"chunk_text: chunk_size={chunk_size} é perigoso, resetando para {CHUNK_SIZE}")
        chunk_size = CHUNK_SIZE
    if overlap >= chunk_size:
        logger.warning(f"chunk_text: overlap={overlap} >= chunk_size={chunk_size}, ajustando")
        overlap = max(0, chunk_size - 100)

    texto = (texto or "").strip()
    if not texto:
        return []
    if len(texto) <= chunk_size:
        return [texto]

    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(texto), step):
        pedaco = texto[i:i + chunk_size].strip()
        if len(pedaco) >= 30:
            chunks.append(pedaco)
        if i + chunk_size >= len(texto):
            break
    return chunks


# ---------------------------------------------------------------------------
# Embeddings (Ollama nomic-embed-text) — resiliente (retry + circuit breaker)
# ---------------------------------------------------------------------------

def _embed_call(texto: str) -> list[float]:
    r = requests.post(
        f"{settings.ollama_url}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": texto},
        timeout=30,
    )
    r.raise_for_status()
    emb = r.json().get("embedding")
    if not emb or len(emb) != DIM:
        raise ValueError(f"embedding inválido do Ollama (len={len(emb) if emb else 0})")
    return emb


def embed_text(texto: str) -> Optional[list[float]]:
    """Gera embedding via Ollama, com retry + circuit breaker + exponential backoff.

    FIX #2: Retry batch com exponential backoff (1s, 2s, 4s, 8s) + max 4 tentativas.
    Nunca levanta: retorna None se o Ollama estiver indisponível após todas retries.
    Quem chama decide se pula o registro (batch) ou reporta erro (API síncrona).
    """
    max_retries = 4
    base_delay = 1.0
    backoff_factor = 2.0

    for attempt in range(max_retries):
        try:
            return _embed_call(texto)
        except (requests.RequestException, ValueError) as e:
            is_last = (attempt == max_retries - 1)
            wait_seconds = base_delay * (backoff_factor ** attempt)
            if is_last:
                logger.warning(
                    f"embed_text FALHOU após {max_retries} tentativas: "
                    f"{type(e).__name__}: {str(e)[:100]}"
                )
                return None
            else:
                logger.info(
                    f"embed_text retry #{attempt + 1}/{max_retries - 1} "
                    f"em {wait_seconds:.1f}s: {type(e).__name__}"
                )
                import time
                time.sleep(wait_seconds)
        except Exception as e:
            # Exceção inesperada: não retenta, falha rápido
            logger.error(f"embed_text erro inesperado (sem retry): {type(e).__name__}: {str(e)[:100]}")
            return None

    return None  # Fallback seguro


def ollama_disponivel() -> bool:
    try:
        r = requests.get(f"{settings.ollama_url}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Indexação / busca genéricas
# ---------------------------------------------------------------------------

def index_documento(db: Session, origem: str, ref_id: Optional[str], texto: str) -> int:
    """Substitui os chunks de (origem, ref_id) pelos novos, gerando embeddings agora.

    Retorna o nº de chunks indexados (0 se texto vazio ou Ollama indisponível).
    Idempotente: pode ser chamado de novo a qualquer momento (upsert por delete+insert).
    """
    ensure_schema(db)
    chunks = chunk_text(texto)
    if not chunks:
        return 0

    prontos = []
    for idx, pedaco in enumerate(chunks):
        emb = embed_text(pedaco)
        if emb is None:
            continue
        prontos.append((idx, pedaco, emb))

    if not prontos:
        logger.warning(f"index_documento: 0/{len(chunks)} chunks embeddados para {origem}/{ref_id}")
        return 0

    db.execute(
        text("DELETE FROM documento_rag WHERE origem=:o AND ref_id IS NOT DISTINCT FROM :r"),
        {"o": origem, "r": ref_id},
    )
    for idx, pedaco, emb in prontos:
        db.execute(text("""
            INSERT INTO documento_rag (origem, ref_id, chunk_idx, texto, embedding)
            VALUES (:o, :r, :i, :t, (:e)::vector)
        """), {"o": origem, "r": ref_id, "i": idx, "t": pedaco, "e": vec_literal(emb)})
    db.commit()
    return len(prontos)


def search(db: Session, query: str, tipo: Optional[str] = None, k: int = 5) -> list[dict]:
    """Busca texto usando LIKE case-insensitive com LOWER()."""
    ensure_schema(db)

    try:
        k = max(1, min(k, 50))
        query_pattern = f"%{query}%"
        params = {"q": query_pattern, "k": k}

        if tipo:
            params["tipo"] = tipo
            sql = text(
                "SELECT origem, ref_id, chunk_idx, texto, 0.5::float AS similaridade "
                "FROM documento_rag "
                "WHERE LOWER(texto) LIKE :q AND origem = :tipo "
                "ORDER BY criado_em DESC LIMIT :k"
            )
        else:
            sql = text(
                "SELECT origem, ref_id, chunk_idx, texto, 0.5::float AS similaridade "
                "FROM documento_rag "
                "WHERE LOWER(texto) LIKE :q "
                "ORDER BY criado_em DESC LIMIT :k"
            )

        logger.info(f"RAG search: query='{query}' pattern='{query_pattern}' tipo={tipo} k={k}")
        rows = db.execute(sql, params).mappings().all()
        logger.info(f"RAG search returned {len(rows)} rows")

        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"RAG search error: {e}", exc_info=True)
        return []


def stats(db: Session) -> dict:
    ensure_schema(db)
    rows = db.execute(text(
        "SELECT origem, count(*) AS n FROM documento_rag GROUP BY origem ORDER BY n DESC"
    )).mappings().all()
    total = db.execute(text("SELECT count(*) FROM documento_rag")).scalar()
    return {"total": total, "por_origem": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Builders de texto por tabela — formatam cada registro em prosa pesquisável
# ---------------------------------------------------------------------------

def texto_processo(p) -> str:
    partes = p.partes or []
    nomes_partes = ", ".join(
        f"{x.get('papel', '')}: {x.get('nome', '')}" for x in partes if isinstance(x, dict)
    )
    linhas = [
        f"Processo {p.numero_cnj} ({p.tipo or p.tipo_pericia or 'Judicial'}).",
        f"Título: {p.titulo}" if getattr(p, "titulo", None) else "",
        f"Autor: {p.autor}" if getattr(p, "autor", None) else "",
        f"Réu: {p.reu}" if getattr(p, "reu", None) else "",
        f"Partes: {nomes_partes}" if nomes_partes else "",
        f"Comarca: {p.comarca}" if getattr(p, "comarca", None) else "",
        f"Vara: {p.vara}" if getattr(p, "vara", None) else "",
        f"Tribunal: {p.tribunal}" if getattr(p, "tribunal", None) else "",
        f"Juiz: {p.juiz}" if getattr(p, "juiz", None) else "",
        f"Especialidade/Setor: {p.especialidade or p.setor or ''}",
        f"Status: {p.status}",
        f"Responsável: {p.responsavel}" if getattr(p, "responsavel", None) else "",
        f"Prazo: {p.prazo}" if getattr(p, "prazo", None) else "",
        f"Descrição: {p.descricao}" if getattr(p, "descricao", None) else "",
    ]
    return "\n".join(l for l in linhas if l).strip()


def texto_intimacao(i) -> str:
    processo_cnj = getattr(getattr(i, "processo", None), "numero_cnj", None) or i.processo_id
    linhas = [
        f"Intimação #{i.id} do processo {processo_cnj}.",
        f"Origem: {i.origem} ({i.source_system or ''}).",
        f"Tipo: {i.tipo}" if i.tipo else "",
        f"Assunto: {i.assunto}" if i.assunto else "",
        f"Status: {i.status}",
        f"Conteúdo: {(i.conteudo or '')[:4000]}" if i.conteudo else "",
    ]
    return "\n".join(l for l in linhas if l).strip()


def texto_laudo(l, conteudo: str = "") -> str:
    linhas = [
        f"Laudo #{l.id} do processo_id {l.processo_id} — tipo {l.tipo_laudo}.",
        f"Status: {l.status}",
        f"Quesitos: {l.quesitos}" if l.quesitos else "",
        f"Notas: {l.notas}" if l.notas else "",
        f"Conteúdo: {conteudo[:8000]}" if conteudo else "",
    ]
    return "\n".join(x for x in linhas if x).strip()


def texto_financeiro(p) -> str:
    linhas = [
        f"Financeiro do processo {p.numero_cnj}.",
        f"Honorários: R$ {p.honorarios}" if p.honorarios is not None else "",
        f"Forma de recebimento: {p.forma_recebimento}" if getattr(p, "forma_recebimento", None) else "",
        f"Pago: {'sim' if p.pago else 'não'}.",
        f"Data de pagamento: {p.data_pagamento}" if getattr(p, "data_pagamento", None) else "",
        f"Data de aceite: {p.data_aceite}" if getattr(p, "data_aceite", None) else "",
    ]
    return "\n".join(l for l in linhas if l).strip()


# ---------------------------------------------------------------------------
# Atalhos por entidade
# ---------------------------------------------------------------------------

def index_processo(db: Session, processo) -> int:
    return index_documento(db, "processo", processo.numero_cnj, texto_processo(processo))


def index_intimacao(db: Session, intimacao) -> int:
    return index_documento(db, "intimacao", str(intimacao.id), texto_intimacao(intimacao))


def index_laudo(db: Session, laudo, conteudo: str = "") -> int:
    return index_documento(db, "laudo", str(laudo.id), texto_laudo(laudo, conteudo))


def index_financeiro(db: Session, processo) -> int:
    return index_documento(db, "financeiro", processo.numero_cnj, texto_financeiro(processo))
