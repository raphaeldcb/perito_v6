from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import uuid
from datetime import datetime
from app.services.forensic_orchestrator import ForensicOrchestrator
from app.models.analise_forense import AnaliseForenseResultado
from app.services.database import SessionLocal
from app.services.forensic_laudo_docx_generator import ForensicLaudoDocxGenerator
from app.services.forensic_docx_to_pdf import ForensicDocxToPdf
from app.services.email_service import EmailService
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/forensic", tags=["forensic"])

# Armazenar jobs em memória (em produção, usar banco)
jobs_cache = {}

@router.post("/analyze")
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

        # Send email notification (non-blocking — log warning on failure)
        try:
            email_svc = EmailService()
            # Prepare analise dict for email notification
            analise_email = {
                "arquivo": file.filename or "documento",
                "confianca": result.get('confianca_consenso', 0),
                "tipo_pericia": result.get('tipo_pericia', 'Não determinado'),
                "setor": result.get('setor', 'Não determinado'),
                "riscos": result.get('nivel_risco', 'Não determinado'),
                "campos_extraidos": result.get('campos_extraidos', {}),
            }
            # Call email service asynchronously (non-blocking)
            usuario_id = 1  # TODO: Get from JWT/session context
            email_result = await email_svc.enviar_notificacao(usuario_id, analise_email)
            if not email_result:
                logger.warning(
                    f"Email notification failed, but processing continues | "
                    f"arquivo: {file.filename} | usuario_id: {usuario_id}"
                )
        except Exception as e:
            logger.warning(
                f"Email notification failed with exception, but processing continues | "
                f"arquivo: {file.filename} | erro: {e}"
            )

        # Limpar
        os.remove(temp_path)
        db.close()

        return JSONResponse(result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{job_id}")
def get_result(job_id: str):
    """Recuperar resultado de análise"""
    db = SessionLocal()
    analise = db.query(AnaliseForenseResultado).filter_by(id=job_id).first()
    db.close()
    
    if not analise:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    
    return analise.resultado_json

@router.post("/{job_id}/sign")
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


@router.get("/{analysis_id}/laudo-docx", tags=["forensic"])
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


@router.get("/{analysis_id}/laudo-pdf", tags=["forensic"])
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
