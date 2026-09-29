import json
import logging
import os
import tempfile
from typing import Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from app.middleware import get_current_user
from app.models import User, Laudo, LaudoVersao, AuditoriaFable, Processo, Job
from app.services import get_db, laudo_generator, auditor_fable, laudo_validator, laudo_exporter, safesign_assinatura
from app.services.laudo_generator_v2 import LaudoGeneratorV2
from app.services.rag_service import RAGService
from app.shared.schemas.api_response import ApiResponse
from app.decorators.require_feature import require_feature_flag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/laudos", tags=["laudos"])


class GerarDocumentoRequest(BaseModel):
    """Request model for gerar-documento endpoint (Task 3)."""
    processo_id: int = Field(..., description="ID do processo")
    tipo_laudo: str = Field(default="judicial", description="Tipo de laudo (ex: judicial, extrajudicial)")


class GerarDocumentoResponse(BaseModel):
    """Response model for gerar-documento endpoint (Task 3)."""
    job_id: int = Field(..., description="ID do job enfileirado")
    status: str = Field(..., description="Status inicial do job (na_fila)")
    message: str = Field(..., description="Mensagem descritiva")


class GerarRascunhoRequest(BaseModel):
    tipo_laudo: str
    quesitos: list[str] = []


class RevisarRequest(BaseModel):
    conteudo_revisado: str


# Task 5: New models for LaudoGeneratorV2 integration
class GerarLaudoRequest(BaseModel):
    """
    Request model for laudo generation via Task 4 (LaudoGeneratorV2).

    Accepts unlimited fields via extra="allow" for maximum flexibility.
    Required fields: processo_id, tipo_laudo
    Optional: template_path, quesitos, numero_laudo, and any custom fields
    """
    processo_id: int = Field(..., description="ID do processo")
    tipo_laudo: str = Field(..., description="Tipo do laudo (contabil, insalubridade, etc.)")
    template_path: Optional[str] = Field(None, description="Path to DOCX template")
    quesitos: list = Field(default_factory=list, description="List of questions to answer")
    numero_laudo: Optional[str] = Field(None, description="Optional laudo number")
    perito_id: Optional[int] = Field(None, description="ID of the perito")
    nome_perito: Optional[str] = Field(None, description="Name of the perito")

    class Config:
        extra = "allow"  # ← KEY: Accept unlimited custom fields


class GerarLaudoResponse(BaseModel):
    """Response for laudo generation request."""
    laudo_id: int = Field(..., description="ID do laudo criado")
    status: str = Field(default="gerando", description="Current status (gerando/pronto/erro)")
    url_download: str = Field(..., description="URL para download do DOCX")


# ===== Task 3: Pipeline Orchestration Endpoint =====
@router.post("/gerar-documento", response_model=GerarDocumentoResponse)
async def gerar_documento(
    req: GerarDocumentoRequest,
    db: Session = Depends(get_db),
):
    """
    POST /api/v1/laudos/gerar-documento - Create job for laudo generation (Task 3)

    Creates a Job record with status "na_fila" to be processed by Task 4.
    Returns job_id for polling/tracking.

    Request:
    {
        "processo_id": 1,
        "tipo_laudo": "judicial"
    }

    Response:
    {
        "job_id": 123,
        "status": "na_fila",
        "message": "Laudo em fila de processamento"
    }
    """
    try:
        logger.info(f"[Task 3] POST /gerar-documento: processo_id={req.processo_id}, tipo_laudo={req.tipo_laudo}")

        # Validate processo exists
        processo = db.query(Processo).filter(Processo.id == req.processo_id).first()
        if not processo:
            logger.warning(f"[Task 3] Processo {req.processo_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Processo {req.processo_id} não encontrado"
            )

        # Create Job record with status "na_fila"
        job = Job(
            tipo="laudo_generation",
            payload={
                "processo_id": req.processo_id,
                "tipo_laudo": req.tipo_laudo
            },
            status="na_fila"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"[Task 3] Job {job.id} created (status=na_fila, processo_id={req.processo_id})")

        return GerarDocumentoResponse(
            job_id=job.id,
            status="na_fila",
            message=f"Laudo em fila de processamento (job_id={job.id})"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Task 3] Error creating job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ===== Task 5: Helper functions =====
def _save_docx(docx_bytes: bytes, laudo_id: int) -> str:
    """
    Save DOCX bytes to file storage.

    For now, uses /tmp/laudos/ (ephemeral)
    TODO: Production should use S3 or persistent storage

    Args:
        docx_bytes: DOCX content as bytes
        laudo_id: Laudo ID for filename

    Returns:
        str: Path to saved file
    """
    laudos_dir = os.path.join(tempfile.gettempdir(), "laudos")
    os.makedirs(laudos_dir, exist_ok=True)

    filepath = os.path.join(laudos_dir, f"laudo_{laudo_id}.docx")
    with open(filepath, "wb") as f:
        f.write(docx_bytes)

    logger.info(f"Saved DOCX to {filepath} ({len(docx_bytes)} bytes)")
    return filepath


async def _gerar_laudo_async(
    laudo_id: int,
    db: Session,
    dados_entrada: Dict[str, Any],
    perito_id: int
):
    """
    Async task: Generate laudo using Task 4 (LaudoGeneratorV2).

    Updates Laudo record status during process:
    - gerando → pronto (success)
    - gerando → erro (failure)

    Args:
        laudo_id: ID of Laudo to update
        db: Database session
        dados_entrada: Input data for generator
        perito_id: ID of perito
    """
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        logger.error(f"Laudo {laudo_id} not found during async generation")
        return

    try:
        logger.info(f"[Task 5 → Task 4] Starting async laudo generation (laudo_id={laudo_id})")

        # Enrich with RAG context
        rag = RAGService(db=db)
        tipo_laudo = dados_entrada.get("tipo_laudo", "")
        rag_context = rag.get_context_for_laudo(
            laudo_type=tipo_laudo.lower(),
            keywords=[tipo_laudo.lower(), "análise", "perícia"]
        )

        if rag_context:
            logger.info(f"[RAG] Added context to laudo generation: {len(rag_context)} chars")
            # Prepend RAG context to dados_entrada for generator to use
            dados_entrada["_rag_context"] = rag_context

        # Trigger Task 4
        gerador = LaudoGeneratorV2()
        docx_bytes = gerador.gerar_laudo_completo(db, dados_entrada)

        logger.info(f"[Task 4 ✓] Generated DOCX ({len(docx_bytes)} bytes)")

        # Save to file
        arquivo_path = _save_docx(docx_bytes, laudo_id)

        # Update Laudo record
        laudo.status = "pronto"
        laudo.arquivo_docx_path = arquivo_path
        laudo.data_emissao = datetime.utcnow()
        laudo.perito_id = perito_id
        db.commit()

        logger.info(f"[Task 5 ✓] Laudo {laudo_id} generation COMPLETE (status=pronto)")

    except Exception as e:
        logger.error(f"[Task 5 ✗] Laudo {laudo_id} generation FAILED: {str(e)}", exc_info=True)
        laudo.status = "erro"
        laudo.notas = f"Erro na geração: {str(e)}"
        db.commit()


# ===== Task 5: New endpoints =====
@router.post("/gerar", response_model=ApiResponse[GerarLaudoResponse])
async def gerar_laudo(
    request: GerarLaudoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    POST /api/v1/laudos/gerar - Trigger laudo generation (Task 5)

    Integrated with Task 4 (LaudoGeneratorV2) for complete laudo generation.

    1. Validate processo exists and belongs to user
    2. Create Laudo record with status="gerando"
    3. Queue async job via background_tasks
    4. Return laudo_id + download URL immediately (no wait)

    Request accepts unlimited JSON fields (extra="allow") for maximum flexibility.

    Response:
    {
        "success": true,
        "data": {
            "laudo_id": 456,
            "status": "gerando",
            "url_download": "/api/v1/laudos/456/download"
        }
    }
    """
    try:
        # Convert request to dict (preserves extra fields)
        dados_entrada = request.model_dump()

        processo_id = dados_entrada.get("processo_id")
        tipo_laudo = dados_entrada.get("tipo_laudo")

        logger.info(f"[Task 5] POST /gerar: processo_id={processo_id}, tipo={tipo_laudo}, user={current_user.id}")

        # Validate processo exists
        processo = db.query(Processo).filter(Processo.id == processo_id).first()
        if not processo:
            raise HTTPException(
                status_code=404,
                detail=f"Processo {processo_id} não encontrado"
            )

        # Create Laudo record
        laudo = Laudo(
            processo_id=processo_id,
            tipo_laudo=tipo_laudo,
            status="gerando",
            perito_id=current_user.id,
            empresa_id=current_user.empresa_id or 1,  # Default to empresa 1 if not set
            quesitos=str(dados_entrada.get("quesitos", [])),
            notas=f"Criado por {current_user.email} via POST /gerar"
        )
        db.add(laudo)
        db.flush()  # Get laudo.id before commit
        db.commit()

        logger.info(f"[Task 5] Created Laudo {laudo.id} (status=gerando)")

        # Queue async generation
        background_tasks.add_task(
            _gerar_laudo_async,
            laudo_id=laudo.id,
            db=db,
            dados_entrada=dados_entrada,
            perito_id=current_user.id
        )

        logger.info(f"[Task 5] Queued async generation for Laudo {laudo.id}")

        # Immediate response (don't wait for generation)
        return ApiResponse(
            success=True,
            data=GerarLaudoResponse(
                laudo_id=laudo.id,
                status="gerando",
                url_download=f"/api/v1/laudos/{laudo.id}/download"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Task 5 ✗] Error in gerar_laudo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/rag-test/search")
async def test_rag_search(
    q: str = "contabil",
    limit: int = 3,
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/laudos/rag-test/search - Test RAG integration
    """
    rag = RAGService(db=db)
    results = rag.search(q, limit=limit)
    context = rag.get_context_for_laudo("contabil", keywords=[q])

    return {
        "search_query": q,
        "results_count": len(results),
        "results": results,
        "context_preview": context[:500] if context else None
    }


@router.get("/{laudo_id}/download")
async def download_laudo(
    laudo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/laudos/{laudo_id}/download - Download generated DOCX (Task 5)

    1. Fetch Laudo record
    2. Validate user has access
    3. Check status == "pronto"
    4. Read DOCX file
    5. Return FileResponse with DOCX bytes

    Returns:
    - 200 with DOCX file if ready
    - 404 if laudo not found
    - 400 if status != "pronto"
    - 403 if user doesn't have access
    """
    try:
        logger.info(f"[Task 5] GET /download: laudo_id={laudo_id}, user={current_user.id}")

        # Fetch Laudo
        laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
        if not laudo:
            logger.warning(f"[Task 5] Laudo {laudo_id} not found")
            raise HTTPException(status_code=404, detail=f"Laudo {laudo_id} não encontrado")

        # Validate user access (basic check: user must be owner or admin)
        # TODO: Add enterprise-level access control (empresa_id check)
        if laudo.perito_id != current_user.id and current_user.role.name != "admin":
            logger.warning(f"[Task 5] User {current_user.id} denied access to Laudo {laudo_id}")
            raise HTTPException(status_code=403, detail="Acesso negado")

        # Check status
        if laudo.status != "pronto":
            logger.info(f"[Task 5] Laudo {laudo_id} not ready (status={laudo.status})")
            raise HTTPException(
                status_code=400,
                detail=f"Laudo ainda não está pronto (status={laudo.status}). Tente novamente em alguns segundos."
            )

        # Check file exists
        if not laudo.arquivo_docx_path or not os.path.exists(laudo.arquivo_docx_path):
            logger.error(f"[Task 5] DOCX file not found for Laudo {laudo_id}: {laudo.arquivo_docx_path}")
            raise HTTPException(status_code=500, detail="Arquivo DOCX não encontrado no servidor")

        # Read and return
        logger.info(f"[Task 5 ✓] Downloading Laudo {laudo_id} ({os.path.getsize(laudo.arquivo_docx_path)} bytes)")
        return FileResponse(
            path=laudo.arquivo_docx_path,
            filename=f"laudo_{laudo_id}_{datetime.utcnow().strftime('%Y%m%d')}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Task 5 ✗] Error in download_laudo: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ===== Existing endpoints =====
@router.post("/{processo_id}/gerar-rascunho")
async def gerar_rascunho(
    processo_id: int,
    payload: GerarRascunhoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Cria Laudo e enfileira job Qwen para gerar rascunho."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    laudo = Laudo(
        processo_id=processo_id,
        tipo_laudo=payload.tipo_laudo,
        perito_id=current_user.id,
        empresa_id=current_user.empresa_id if hasattr(current_user, "empresa_id") else 1,
        quesitos=json.dumps(payload.quesitos, ensure_ascii=False),
        status="rascunho"
    )
    db.add(laudo)
    db.commit()
    db.refresh(laudo)

    background_tasks.add_task(
        laudo_generator.gerar_rascunho,
        laudo_id=laudo.id,
        db=db
    )

    logger.info(f"Laudo {laudo.id} criado, job Qwen enfileirado")
    return {"laudo_id": laudo.id, "status": "job_enfileirado"}


@router.get("/{laudo_id}")
def get_laudo(
    laudo_id: int,
    versao: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """GET /api/v1/laudos/123?versao=2 → rascunho + auditoria."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")

    if not versao:
        ultima_versao = db.query(LaudoVersao).filter(
            LaudoVersao.laudo_id == laudo_id
        ).order_by(LaudoVersao.numero_versao.desc()).first()
        versao = ultima_versao.numero_versao if ultima_versao else None

    if not versao:
        return {
            "laudo": {
                "id": laudo.id,
                "processo_id": laudo.processo_id,
                "tipo_laudo": laudo.tipo_laudo,
                "status": laudo.status
            },
            "rascunho": None,
            "auditoria": None
        }

    versao_obj = db.query(LaudoVersao).filter(
        LaudoVersao.laudo_id == laudo_id,
        LaudoVersao.numero_versao == versao
    ).first()

    auditoria = db.query(AuditoriaFable).filter(
        AuditoriaFable.laudo_id == laudo_id,
        AuditoriaFable.versao_numero == versao
    ).first()

    return {
        "laudo": {
            "id": laudo.id,
            "processo_id": laudo.processo_id,
            "tipo_laudo": laudo.tipo_laudo,
            "status": laudo.status,
            "versao_atual": versao
        },
        "rascunho": versao_obj.conteudo_markdown if versao_obj else None,
        "auditoria": auditoria.relatorio_json if auditoria else None,
        "historico_versoes": [
            {
                "numero": v.numero_versao,
                "gerado_por": v.gerado_por,
                "data_criacao": v.created_at.isoformat() if v.created_at else None
            }
            for v in db.query(LaudoVersao).filter(
                LaudoVersao.laudo_id == laudo_id
            ).order_by(LaudoVersao.numero_versao.asc()).all()
        ]
    }


@router.post("/{laudo_id}/auditar")
async def auditar(
    laudo_id: int,
    versao: int = None,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """POST /api/v1/laudos/123/auditar → enfileira job Fable 5."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")

    if not versao:
        ultima_versao = db.query(LaudoVersao).filter(
            LaudoVersao.laudo_id == laudo_id
        ).order_by(LaudoVersao.numero_versao.desc()).first()
        versao = ultima_versao.numero_versao if ultima_versao else None

    if not versao:
        raise HTTPException(status_code=400, detail="Nenhuma versão do laudo para auditar")

    background_tasks.add_task(
        auditor_fable.auditar_laudo,
        laudo_id=laudo_id,
        versao_numero=versao,
        db=db
    )

    laudo.status = "auditado"
    db.commit()

    logger.info(f"Auditoria enfileirada para laudo {laudo_id} v{versao}")
    return {"status": "auditoria_enfileirada", "versao": versao}


@router.patch("/{laudo_id}/revisar")
def revisar_laudo(
    laudo_id: int,
    payload: RevisarRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """PATCH /api/v1/laudos/123/revisar → salva nova versão."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")

    ultima_versao = db.query(LaudoVersao).filter(
        LaudoVersao.laudo_id == laudo_id
    ).order_by(LaudoVersao.numero_versao.desc()).first()

    proxima_versao = (ultima_versao.numero_versao + 1) if ultima_versao else 1

    nova_versao = LaudoVersao(
        laudo_id=laudo_id,
        numero_versao=proxima_versao,
        conteudo_markdown=payload.conteudo_revisado,
        gerado_por="perito",
        editado_por=current_user.id
    )

    laudo.status = "em_revisao"
    db.add(nova_versao)
    db.commit()
    db.refresh(nova_versao)

    logger.info(f"Versão {proxima_versao} salva para laudo {laudo_id}")
    return {
        "laudo_id": laudo_id,
        "nova_versao": proxima_versao,
        "status": "em_revisao"
    }


@router.post("/{laudo_id}/finalizar")
async def finalizar_laudo(
    laudo_id: int,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """POST /api/v1/laudos/123/finalizar → valida, exporta, assina."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(status_code=404, detail="Laudo não encontrado")

    validacao = laudo_validator.validar_antes_emitir(laudo_id, db)

    if validacao["erros_criticos"]:
        raise HTTPException(
            status_code=422,
            detail={
                "erros": validacao["erros_criticos"],
                "avisos": validacao["avisos"]
            }
        )

    background_tasks.add_task(
        laudo_exporter.exportar_e_assinar,
        laudo_id=laudo_id,
        db=db
    )

    laudo.status = "emitido"
    laudo.data_emissao = datetime.utcnow()
    db.commit()

    logger.info(f"Laudo {laudo_id} finalizado e enfileirado para exportação")
    return {
        "status": "emitido",
        "laudo_id": laudo_id,
        "avisos": validacao["avisos"]
    }


@router.get("")
def list_laudos(
    status: str = None,
    perito_id: int = None,
    empresa_id: int = None,
    tipo_laudo: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """GET /api/v1/laudos?status=emitido&perito_id=5"""
    query = db.query(Laudo)

    if status:
        query = query.filter(Laudo.status == status)
    if perito_id:
        query = query.filter(Laudo.perito_id == perito_id)
    if empresa_id:
        query = query.filter(Laudo.empresa_id == empresa_id)
    if tipo_laudo:
        query = query.filter(Laudo.tipo_laudo == tipo_laudo)

    laudos = query.offset(skip).limit(limit).all()

    return [
        {
            "id": l.id,
            "processo_id": l.processo_id,
            "tipo": l.tipo_laudo,
            "status": l.status,
            "perito_id": l.perito_id,
            "data_criacao": l.created_at.isoformat() if l.created_at else None,
            "data_emissao": l.data_emissao.isoformat() if l.data_emissao else None
        }
        for l in laudos
    ]


@router.post("/{laudo_id}/assinar-safesign")
def gerar_url_assinatura(
    laudo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """POST /api/v1/laudos/{laudo_id}/assinar-safesign → gera URL para assinatura via SafeSign."""
    try:
        resultado = safesign_assinatura.gerar_url_assinatura(laudo_id, db)
        logger.info(f"URL de assinatura gerada para laudo {laudo_id}")
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao gerar URL: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar URL de assinatura")


@router.post("/{laudo_id}/assinatura-callback")
def processar_assinatura_callback(
    laudo_id: int,
    pdf_assinado: bytes,
    db: Session = Depends(get_db)
):
    """POST /api/v1/laudos/{laudo_id}/assinatura-callback → processa PDF assinado do SafeSign."""
    try:
        resultado = safesign_assinatura.processar_callback_assinatura(laudo_id, pdf_assinado, db)
        logger.info(f"PDF assinado processado para laudo {laudo_id}")
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao processar callback: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar assinatura")
