"""
IA module routes (modularized).
Endpoints: IA-01 to IA-05 (analyze, search, chat, history, index).
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.services import get_db
from app.middleware import get_current_user
from app.middleware.rate_limiting import limiter
from app.shared.schemas import ApiResponse, PaginationMeta, PaginatedResponse
from app.shared.exceptions import (
    ValidationException,
    AuthenticationException,
    ResourceNotFoundException,
    ExternalServiceException,
)
from app.models import User

from app.modules.ia.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    RAGSearchRequest,
    RAGContextSchema,
    ChatRequest,
    ChatResponse,
)
from app.modules.ia.repositories import AnalysisRepository
from app.modules.ia.services import get_qwen_service, get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ia", tags=["ia"])


# ============================================================================
# IA-01: POST /analyze — Analyze text with Qwen
# ============================================================================
@router.post("/analyze", response_model=ApiResponse[AnalysisResponse])
@limiter.limit("10/minute")
async def analyze(
    request: Request,
    req: AnalysisRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    IA-01: Analyze text using Qwen LLM.

    Takes arbitrary text and returns structured analysis.
    Optionally uses RAG context for better understanding.

    Rate limited to 10 requests/minute per user.
    """
    try:
        qwen_service = get_qwen_service()
        rag_service = get_rag_service(db)
        repo = AnalysisRepository(db)

        # Get RAG context if available
        rag_context = None
        rag_results = []
        try:
            rag_results = await rag_service.search(
                query=req.text[:500],  # Use first 500 chars as query
                top_k=5,
            )
            rag_context = [r for r in rag_results]
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")

        # Call Qwen
        qwen_result = await qwen_service.analyze(
            text=req.text,
            context=req.context,
        )

        # Store analysis
        analysis = repo.create_analysis(
            user_id=user.id,
            input_text=req.text,
            analysis_result=qwen_result["response"],
            model=qwen_result["model"],
            provider=qwen_result["provider"],
            processo_id=req.processo_id,
            input_tokens=qwen_result.get("input_tokens"),
            output_tokens=qwen_result.get("output_tokens"),
            cost_usd=qwen_result.get("cost_usd", 0.0),
            rag_context={"results": rag_results} if rag_results else None,
        )

        # Format response
        response_data = AnalysisResponse(
            id=analysis.id,
            analysis_result=analysis.analysis_result,
            model=analysis.model,
            provider=analysis.provider,
            input_tokens=analysis.input_tokens,
            output_tokens=analysis.output_tokens,
            cost_usd=analysis.cost_usd,
            status=analysis.status,
            error_detail=analysis.error_detail,
            rag_context=[RAGContextSchema(**r) for r in rag_results] if rag_results else None,
            created_at=analysis.created_at,
        )

        return ApiResponse(
            success=True,
            data=response_data,
        )

    except ExternalServiceException as e:
        # LLM unavailable
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed",
        )


# ============================================================================
# IA-02: POST /search — Semantic RAG search
# ============================================================================
@router.post("/search", response_model=ApiResponse[list[RAGContextSchema]])
@limiter.limit("20/minute")
async def search(
    request: Request,
    req: RAGSearchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    IA-02: Semantic search across RAG corpus.

    Searches embedded documents using cosine similarity.
    Returns top-k most relevant chunks sorted by relevance.
    """
    try:
        rag_service = get_rag_service(db)

        results = await rag_service.search(
            query=req.query,
            top_k=req.top_k,
            area=req.area,
        )

        response_data = [RAGContextSchema(**r) for r in results]

        return ApiResponse(
            success=True,
            data=response_data,
        )

    except Exception as e:
        logger.error(f"RAG search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Search failed",
        )


# ============================================================================
# IA-03: POST /chat — Stateless chat with context
# ============================================================================
@router.post("/chat", response_model=ApiResponse[ChatResponse])
@limiter.limit("15/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    IA-03: Stateless conversational chat with IA.

    Combines Qwen analysis with optional RAG context.
    Each request is independent (no conversation history).

    Rate limited to 15 requests/minute per user.
    """
    try:
        qwen_service = get_qwen_service()
        rag_service = get_rag_service(db)
        repo = AnalysisRepository(db)

        # Get RAG context if enabled
        rag_results = []
        if req.use_rag:
            try:
                rag_results = await rag_service.search(
                    query=req.message,
                    top_k=3,
                )
            except Exception as e:
                logger.warning(f"RAG context retrieval failed: {e}")

        # Build augmented prompt
        augmented_text = req.message
        if rag_results:
            context_text = "\n\n".join([
                f"Referência {i+1}: {r['content'][:500]}"
                for i, r in enumerate(rag_results[:3])
            ])
            augmented_text = f"{req.message}\n\nContexto RAG:\n{context_text}"

        # Call Qwen
        qwen_result = await qwen_service.analyze(
            text=augmented_text,
            context=req.context,
        )

        # Store as analysis record
        analysis = repo.create_analysis(
            user_id=user.id,
            input_text=req.message,
            analysis_result=qwen_result["response"],
            model=qwen_result["model"],
            provider=qwen_result["provider"],
            processo_id=req.processo_id,
            input_tokens=qwen_result.get("input_tokens"),
            output_tokens=qwen_result.get("output_tokens"),
            cost_usd=qwen_result.get("cost_usd", 0.0),
            rag_context={"results": rag_results} if rag_results else None,
        )

        response_data = ChatResponse(
            id=analysis.id,
            message=qwen_result["response"],
            rag_context=[RAGContextSchema(**r) for r in rag_results] if rag_results else None,
            tokens_used={
                "input": qwen_result.get("input_tokens", 0),
                "output": qwen_result.get("output_tokens", 0),
            },
            created_at=analysis.created_at,
        )

        return ApiResponse(
            success=True,
            data=response_data,
        )

    except ExternalServiceException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Chat failed",
        )


# ============================================================================
# IA-04: GET /history — Get analysis history for user
# ============================================================================
@router.get("/history", response_model=PaginatedResponse[AnalysisResponse])
@limiter.limit("20/minute")
async def get_history(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    IA-04: Get analysis history for current user.

    Returns paginated list of past analyses sorted by recency.
    """
    try:
        if page < 1 or page_size < 1 or page_size > 100:
            raise ValidationException("Invalid pagination parameters")

        repo = AnalysisRepository(db)

        offset = (page - 1) * page_size
        analyses, total = repo.get_user_analyses(
            user_id=user.id,
            limit=page_size,
            offset=offset,
        )

        # Format response
        data = [
            AnalysisResponse(
                id=a.id,
                analysis_result=a.analysis_result[:500],  # Truncate for list
                model=a.model,
                provider=a.provider,
                input_tokens=a.input_tokens,
                output_tokens=a.output_tokens,
                cost_usd=a.cost_usd,
                status=a.status,
                error_detail=a.error_detail,
                rag_context=None,  # Don't include full context in history
                created_at=a.created_at,
            )
            for a in analyses
        ]

        total_pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            success=True,
            data=data,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"History retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="History retrieval failed",
        )


# ============================================================================
# IA-05: GET /analyses/{id} — Get single analysis with full context
# ============================================================================
@router.get("/analyses/{analysis_id}", response_model=ApiResponse[AnalysisResponse])
@limiter.limit("30/minute")
async def get_analysis(
    request: Request,
    analysis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    IA-05: Get single analysis by ID with full context.

    Returns complete analysis including RAG results.
    """
    try:
        repo = AnalysisRepository(db)
        analysis = repo.get_analysis_by_id(analysis_id)

        if not analysis:
            raise ResourceNotFoundException(
                f"Analysis {analysis_id} not found",
                error_code="ANALYSIS_NOT_FOUND",
            )

        # Check authorization (user can only see their own)
        if analysis.user_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this analysis",
            )

        # Format RAG context
        rag_context = []
        if analysis.rag_context:
            try:
                rag_data = analysis.rag_context.get("results", [])
                rag_context = [RAGContextSchema(**r) for r in rag_data]
            except Exception as e:
                logger.warning(f"Failed to parse RAG context: {e}")

        response_data = AnalysisResponse(
            id=analysis.id,
            analysis_result=analysis.analysis_result,
            model=analysis.model,
            provider=analysis.provider,
            input_tokens=analysis.input_tokens,
            output_tokens=analysis.output_tokens,
            cost_usd=analysis.cost_usd,
            status=analysis.status,
            error_detail=analysis.error_detail,
            rag_context=rag_context if rag_context else None,
            created_at=analysis.created_at,
        )

        return ApiResponse(
            success=True,
            data=response_data,
        )

    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"Analysis retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Analysis retrieval failed",
        )
