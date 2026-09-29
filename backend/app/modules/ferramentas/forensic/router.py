"""Forensic analysis and laudo routes."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
import uuid
from datetime import datetime
from pathlib import Path
import os
import logging
from sqlalchemy.orm import Session

from app.services.forensic_orchestrator import ForensicOrchestrator
from app.models.analise_forense import AnaliseForenseResultado
from app.models import User, LaudoForense, ClienteForense, Job
from app.services.database import SessionLocal
from app.services.forensic_laudo_docx_generator import ForensicLaudoDocxGenerator
from app.services.forensic_docx_to_pdf import ForensicDocxToPdf
from app.middleware import get_current_user
from app.services import get_db
from app.config import settings

from .schemas import (
    AnalisisResultResponse,
    LaudoForenseCompleto,
    ClienteForenseResponse,
)
from .service import ForensicService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["forensic"])

# Armazenar jobs em memória (em produção, usar banco)
jobs_cache = {}

forensic_service = ForensicService()


# ============================================================================
# Forensic Analysis Endpoints (from forensic_analysis.py)
# ============================================================================

@router.post("/forensic/analyze")
async def analyze_forensic(file: UploadFile = File(...)):
    """Upload e análise forense completa"""
    try:
        # Salvar arquivo temporário
        temp_path = f"/tmp/{uuid.uuid4()}.tmp"
        contents = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(contents)

        # Salvar no BD primeiro (para passar para orchestrator)
        job_id = str(uuid.uuid4())[:8]
        db = SessionLocal()

        analise = AnaliseForenseResultado(
            id=job_id,
            arquivo_hash_md5='',  # Will be filled by orchestrator
            arquivo_nome=file.filename,
            arquivo_tipo=file.content_type,
            arquivo_tamanho_bytes=len(contents),
            resultado_json={},  # Will be filled by orchestrator
            veredicto_final='',  # Will be filled by orchestrator
            confianca_consenso=0.0,  # Will be filled by orchestrator
            nivel_risco='',  # Will be filled by orchestrator
            timestamp_conclusao=datetime.utcnow()
        )

        db.add(analise)
        db.commit()
        db.refresh(analise)

        # Análise assincronamente (com referência ao BD)
        orchestrator = ForensicOrchestrator()
        result = await orchestrator.analyze(temp_path, db_analysis=analise, user_name=None)

        # Atualizar registro com resultados
        analise.arquivo_hash_md5 = result['arquivo_hash']
        analise.resultado_json = result
        analise.veredicto_final = result['veredicto_final']
        analise.confianca_consenso = result['confianca_consenso']
        analise.nivel_risco = result['nivel_risco']
        db.commit()

        # Limpar
        os.remove(temp_path)
        db.close()

        return JSONResponse(result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forensic/result/{job_id}")
def get_result(job_id: str):
    """Recuperar resultado de análise"""
    db = SessionLocal()
    analise = db.query(AnaliseForenseResultado).filter_by(id=job_id).first()
    db.close()

    if not analise:
        raise HTTPException(status_code=404, detail="Análise não encontrada")

    return analise.resultado_json


@router.post("/forensic/{job_id}/sign")
def sign_result(job_id: str):
    """Marcar como assinado (A3)"""
    db = SessionLocal()
    analise = db.query(AnaliseForenseResultado).filter_by(id=job_id).first()

    if not analise:
        raise HTTPException(status_code=404)

    analise.assinado = True
    analise.timestamp_assinatura = datetime.utcnow()
    db.commit()
    db.close()

    return {"assinado": True}


@router.get("/forensic/{analysis_id}/laudo-docx")
async def get_forensic_laudo_docx(analysis_id: str):
    """
    Gera DOCX de laudo forense preenchido.

    Returns:
        - 200: DOCX bytes
        - 404: analysis_id não encontrada
        - 500: Erro ao gerar laudo
    """
    db = SessionLocal()
    try:
        # Buscar análise no banco
        analysis = db.query(AnaliseForenseResultado).filter_by(id=analysis_id).first()

        if not analysis:
            raise HTTPException(status_code=404, detail="Análise não encontrada")

        # Preparar dados para o documento
        resultado_json = analysis.resultado_json or {}

        data = {
            'codigo_laudo': resultado_json.get('codigo_laudo', f"L{analysis.timestamp_criacao.strftime('%Y%m%d')}{analysis.id[:8]}"),
            'contratante': resultado_json.get('contratante', 'Não informado'),
            'objeto': resultado_json.get('objeto', 'Análise forense de mídia'),
            'arquivo_nome': analysis.arquivo_nome or 'Não informado',
            'arquivo_mime': analysis.arquivo_tipo or 'Não informado',
            'arquivo_dimensoes': resultado_json.get('arquivo_dimensoes', 'N/A'),
            'arquivo_tamanho': str(analysis.arquivo_tamanho_bytes) if analysis.arquivo_tamanho_bytes else 'N/A',
            'arquivo_hash_sha256': resultado_json.get('arquivo_hash_sha256', 'N/A'),
            'arquivo_hash_sha1': resultado_json.get('arquivo_hash_sha1', 'N/A'),
            'arquivo_hash_md5': analysis.arquivo_hash_md5 or 'N/A',
            'data_calculo_hash': resultado_json.get('data_calculo_hash', 'N/A'),
            'total_achados': resultado_json.get('total_achados', '0'),
            'total_criticos': resultado_json.get('total_criticos', '0'),
            'total_alertas': resultado_json.get('total_alertas', '0'),
            'total_informativos': resultado_json.get('total_informativos', '0'),
            'confianca': str(round(analysis.confianca_consenso * 100, 2)) if analysis.confianca_consenso else '0',
            'nivel_risco': analysis.nivel_risco or 'DESCONHECIDO',
        }

        # Gerar DOCX
        generator = ForensicLaudoDocxGenerator()
        docx_bytes = generator.generate(data)

        # Extrair código do laudo para o nome do arquivo
        codigo_laudo = data['codigo_laudo']

        return StreamingResponse(
            iter([docx_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=Laudo_{codigo_laudo}.docx"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar laudo DOCX: {e}", exc_info=True)
        # If database table doesn't exist, treat as 404
        if "no such table" in str(e):
            raise HTTPException(status_code=404, detail="Análise não encontrada")
        raise HTTPException(status_code=500, detail="Erro ao gerar laudo")
    finally:
        db.close()


@router.get("/forensic/{analysis_id}/laudo-pdf")
async def get_forensic_laudo_pdf(analysis_id: str):
    """
    Gera PDF de laudo forense (conversão de DOCX via LibreOffice).

    Returns:
        - 200: PDF bytes
        - 404: analysis_id não encontrada
        - 500: Erro ao gerar PDF
    """
    db = SessionLocal()
    try:
        # Buscar análise no banco
        analysis = db.query(AnaliseForenseResultado).filter_by(id=analysis_id).first()

        if not analysis:
            raise HTTPException(status_code=404, detail="Análise não encontrada")

        # Preparar dados para o documento (reutiliza lógica de /laudo-docx)
        resultado_json = analysis.resultado_json or {}

        data = {
            'codigo_laudo': resultado_json.get('codigo_laudo', f"L{analysis.timestamp_criacao.strftime('%Y%m%d')}{analysis.id[:8]}"),
            'contratante': resultado_json.get('contratante', 'Não informado'),
            'objeto': resultado_json.get('objeto', 'Análise forense de mídia'),
            'arquivo_nome': analysis.arquivo_nome or 'Não informado',
            'arquivo_mime': analysis.arquivo_tipo or 'Não informado',
            'arquivo_dimensoes': resultado_json.get('arquivo_dimensoes', 'N/A'),
            'arquivo_tamanho': str(analysis.arquivo_tamanho_bytes) if analysis.arquivo_tamanho_bytes else 'N/A',
            'arquivo_hash_sha256': resultado_json.get('arquivo_hash_sha256', 'N/A'),
            'arquivo_hash_sha1': resultado_json.get('arquivo_hash_sha1', 'N/A'),
            'arquivo_hash_md5': analysis.arquivo_hash_md5 or 'N/A',
            'data_calculo_hash': resultado_json.get('data_calculo_hash', 'N/A'),
            'total_achados': resultado_json.get('total_achados', '0'),
            'total_criticos': resultado_json.get('total_criticos', '0'),
            'total_alertas': resultado_json.get('total_alertas', '0'),
            'total_informativos': resultado_json.get('total_informativos', '0'),
            'confianca': str(round(analysis.confianca_consenso * 100, 2)) if analysis.confianca_consenso else '0',
            'nivel_risco': analysis.nivel_risco or 'DESCONHECIDO',
        }

        # Gerar DOCX
        generator = ForensicLaudoDocxGenerator()
        docx_bytes = generator.generate(data)

        # Converter DOCX → PDF
        converter = ForensicDocxToPdf()
        pdf_bytes = converter.convert(docx_bytes)

        # Extrair código do laudo para o nome do arquivo
        codigo_laudo = data['codigo_laudo']

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Laudo_{codigo_laudo}.pdf"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar laudo PDF: {e}", exc_info=True)
        # If database table doesn't exist, treat as 404
        if "no such table" in str(e):
            raise HTTPException(status_code=404, detail="Análise não encontrada")
        raise HTTPException(status_code=500, detail="Erro ao gerar PDF")
    finally:
        db.close()


# ============================================================================
# Forensic Laudo Endpoints (from forensic_laudo.py)
# ============================================================================

@router.post("/media/forensic-laudo-completo", status_code=201)
async def criar_laudo_forense(
    arquivo: UploadFile = File(...),
    cliente_nome: str = Form(..., min_length=3),
    cliente_cnpj: str = Form(...),
    cliente_email: str = Form(...),
    origem_midia: str = Form(default="Outro"),
    descricao: str = Form(default=""),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Cria novo laudo forense e enfileira análise.

    **Body (multipart/form-data):**
    - arquivo: UploadFile (vídeo/áudio/imagem)
    - cliente_nome: string
    - cliente_cnpj: string (formato: XX.XXX.XXX/0001-XX ou sem formatação)
    - cliente_email: string
    - origem_midia: string (WhatsApp, Email, Pen Drive, Outro)
    - descricao: string (opcional)

    **Response 201:**
    ```json
    {
      "numero_laudo": "LF-2026-08-00001",
      "status": "processando",
      "job_id": "uuid-da-job"
    }
    ```
    """
    return await forensic_service.criar_laudo_forense(
        arquivo=arquivo,
        cliente_nome=cliente_nome,
        cliente_cnpj=cliente_cnpj,
        cliente_email=cliente_email,
        origem_midia=origem_midia,
        descricao=descricao,
        db=db,
    )


@router.get("/media/forensic-laudo/{numero_laudo}")
async def obter_laudo(
    numero_laudo: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Recupera laudo forense completo.

    **Response 200:**
    ```json
    {
      "numero_laudo": "LF-2026-08-00001",
      "cliente": { "nome": "...", "cnpj": "...", "email": "..." },
      "arquivo_hash": "abc123...",
      "veredicto": "APROVADO",
      "authenticity_score": 95.2,
      "consensus": 100.0,
      "status": "processado",
      "pdf_url": "/api/v1/media/forensic-laudo/LF-2026-08-00001/pdf",
      "created_at": "2026-08-05T10:30:00",
      "resultados_apis": [
        { "api": "deepware", "is_fake": false, "confidence": 95.0 },
        ...
      ]
    }
    ```
    """
    return await forensic_service.obter_laudo(numero_laudo=numero_laudo, db=db)


@router.get("/media/forensic-laudo/{numero_laudo}/pdf")
async def download_pdf_laudo(
    numero_laudo: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Download do PDF do laudo forense.
    """
    return await forensic_service.download_pdf_laudo(numero_laudo=numero_laudo, db=db)


@router.get("/media/forensic-laudo")
async def listar_laudos(
    skip: int = 0,
    limit: int = 20,
    status_filtro: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Lista laudos forenses.
    """
    return await forensic_service.listar_laudos(
        skip=skip,
        limit=limit,
        status_filtro=status_filtro,
        db=db,
    )
