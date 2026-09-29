"""RAG Router — Vector search endpoints for semantic access to acervo."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.middleware import get_current_user
from app.middleware.rate_limiting import limiter
from app.models import User
from app.services import get_db
from app.services import rag_indexer
from .schemas import Chunk, IndexarInput, BuscarInput
from . import service

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])
logger = logging.getLogger(__name__)


@router.post("/indexar")
async def indexar(
    payload: IndexarInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Substitui os chunks de (origem, ref_id) pelos novos já embeddados (uso: mac_agent)."""
    try:
        return service.indexar_chunks(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/buscar")
async def buscar(
    payload: BuscarInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Top-k chunks mais similares (cosine) a um embedding já pronto (uso: mac_agent)."""
    try:
        return service.buscar_por_embedding(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search")
@limiter.limit(settings.rate_limit_search)  # ex: 30/minute — protege o Ollama de flood
async def search(
    request: Request,
    q: str = Query(..., min_length=2, description="Texto da busca (linguagem natural)"),
    tipo: str | None = Query(None, description="processo | intimacao | laudo | financeiro"),
    k: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Busca semântica server-side: embedda `q` via Ollama e retorna os top-k trechos
    mais similares. Usada para fundamentar prompts do Qwen (laudo, ofício, etc) com
    contexto histórico real do acervo (processos, intimações, laudos, financeiro)."""
    try:
        return service.search_semantico(db, q, tipo, k)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Ollama indisponível — 503 (indisponibilidade temporária), não 500
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/stats")
async def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Retorna estatísticas do índice RAG."""
    return service.get_stats(db)
