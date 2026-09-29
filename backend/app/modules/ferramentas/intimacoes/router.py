"""Rotas para intimações (court notifications) e modelos.

O download de autos ESAJ exige Chrome + certificado digital, que rodam no Mac
(pipeline v5.3). Este endpoint NÃO baixa nada: ele enfileira um Job que o
mac_agent processa e reporta. O status devolvido é o estado real da fila.
"""
import os
import json as json_lib
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import Intimacao, User
from app.services import get_db

from . import service
from .schemas import (
    ModeloResponse,
    IntimacaoUploadResponse,
    BaixarAutosESAJResponse,
    IntimacaoStatusUpdateRequest,
    IntimacaoResumoResponse,
)

router = APIRouter()


# ====================
# MODELOS ENDPOINTS
# ====================


@router.get("/api/v1/ferramentas/modelos", response_model=list[ModeloResponse], tags=["modelos"])
async def listar_modelos(db: Session = Depends(get_db)):
    """Listar modelos disponíveis"""
    return service.listar_modelos()


@router.get("/api/v1/ferramentas/modelos/{modelo_id}", response_model=ModeloResponse, tags=["modelos"])
async def obter_modelo(modelo_id: int, db: Session = Depends(get_db)):
    """Obter modelo específico"""
    modelo = service.obter_modelo(modelo_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    return modelo


@router.get("/api/v1/ferramentas/modelos/categoria/{categoria}", response_model=list[ModeloResponse], tags=["modelos"])
async def listar_por_categoria(categoria: str, db: Session = Depends(get_db)):
    """Listar modelos por categoria"""
    return service.listar_modelos_por_categoria(categoria)


# ====================
# INTIMACOES ENDPOINTS
# ====================


@router.get("/api/v1/intimacoes", tags=["intimacoes"])
async def listar_intimacoes(
    skip: int = 0,
    limit: int = 20,
    status_filtro: str = None,
    incluir_oportunidades: bool = False,  # 'oportunidade' são leads de captação (DJE), não casos
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Intimacao)
    if status_filtro:
        query = query.filter(Intimacao.status == status_filtro)
    elif not incluir_oportunidades:
        # por padrão, esconde os leads de captação para o painel não ficar poluído
        query = query.filter(Intimacao.status != "oportunidade")

    total = query.count()
    intimacoes = query.order_by(Intimacao.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "items": intimacoes}


@router.post("/api/v1/intimacoes/upload-email", response_model=IntimacaoUploadResponse, tags=["intimacoes"])
async def upload_email_intimacao(
    file: UploadFile = File(...),
    numero_processo: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conteudo = await file.read()

    numero_processo = service.extrair_numero_processo(file.filename, numero_processo)

    if not numero_processo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="numero_processo é obrigatório ou deve constar no nome do arquivo (formato CNJ)",
        )

    processo = service.criar_ou_obter_processo(numero_processo, db)
    pdf_path = service.salvar_intimacao_arquivo(conteudo, numero_processo, file.filename)
    intimacao = service.criar_intimacao_email(processo.id, pdf_path, file.filename, db)

    return {
        "id": intimacao.id,
        "processo_id": processo.id,
        "numero_processo": numero_processo,
        "status": "pendente",
        "message": "Intimação armazenada. Análise entra na fila do worker.",
    }


@router.post("/api/v1/intimacoes/baixar-autos-esaj", response_model=BaixarAutosESAJResponse, tags=["intimacoes"])
async def baixar_autos_esaj(
    numero_processo: str,
    tribunal: str = "TJMS",
    sistema: str = "esaj",  # esaj | eproc (MS está migrando aos poucos)
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enfileira o download dos autos. O mac_agent executa (ESAJ por CPF/senha,
    eproc quando credenciado) e reporta — acompanhe em /api/v1/jobs/{id}."""
    if sistema not in ("esaj", "eproc"):
        raise HTTPException(status_code=400, detail="sistema deve ser 'esaj' ou 'eproc'")

    processo = service.criar_ou_obter_processo(numero_processo, db)
    job = service.enfileirar_download_esaj(numero_processo, tribunal, sistema, processo.id, db)

    return {
        "job_id": job.id,
        "numero_processo": numero_processo,
        "status": job.status,
        "message": "Download enfileirado. O agente Mac executa com certificado digital "
                   "e o status muda para 'concluido' apenas quando o PDF existir.",
    }


@router.get("/api/v1/intimacoes/{intimacao_id}", tags=["intimacoes"])
async def obter_intimacao(
    intimacao_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    intimacao = db.query(Intimacao).filter(Intimacao.id == intimacao_id).first()
    if not intimacao:
        raise HTTPException(status_code=404, detail=f"Intimação {intimacao_id} não encontrada")
    return intimacao


@router.patch("/api/v1/intimacoes/{intimacao_id}/status", tags=["intimacoes"])
async def atualizar_status_intimacao(
    intimacao_id: int,
    request: IntimacaoStatusUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    intimacao = db.query(Intimacao).filter(Intimacao.id == intimacao_id).first()
    if not intimacao:
        raise HTTPException(status_code=404, detail=f"Intimação {intimacao_id} não encontrada")

    if not service.validar_status_intimacao(request.novo_status):
        raise HTTPException(status_code=400, detail=f"Status inválido: {request.novo_status}")

    intimacao.status = request.novo_status
    db.commit()
    return {"id": intimacao.id, "status": request.novo_status}


@router.get("/api/v1/intimacoes/resumo", response_model=IntimacaoResumoResponse, tags=["intimacoes"])
async def resumo_tabular(
    limit: int = 50,
    status_filtro: str = "analisada",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Tabela consolidada de intimações com dados estruturados — para dashboard/export."""
    query = db.query(Intimacao).order_by(Intimacao.updated_at.desc())

    if status_filtro:
        query = query.filter(Intimacao.status == status_filtro)

    intimacoes = query.limit(limit).all()

    resumo = []
    for intim in intimacoes:
        dados = intim.dados_estruturados or {}

        resumo.append(
            {
                "id": intim.id,
                "numero_cnj": intim.processo.numero_cnj if intim.processo else "?",
                "data_processamento": intim.created_at.isoformat() if intim.created_at else None,
                "status": intim.status,
                "juiz": dados.get("juiz", "?"),
                "vara": dados.get("vara", "?"),
                "tipo": dados.get("tipo", "?"),
                "prazo_dias": dados.get("prazo_dias", 0),
                "urgencia": dados.get("urgencia", "?").upper(),
                "resumo": dados.get("resumo", "")[:100],
                "quesitos_count": len(dados.get("quesitos", [])),
                "arquivos": {
                    "pdf": intim.pdf_path,
                    "txt": intim.txt_path,
                    "json": intim.json_path,
                    "md": intim.md_path,
                },
            }
        )

    return {"total": len(resumo), "itens": resumo}


@router.get("/api/v1/intimacoes/{intimacao_id}/arquivo/{tipo}", tags=["intimacoes"])
async def download_arquivo(
    intimacao_id: int,
    tipo: str,  # json, md, txt, pdf
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retorna conteúdo do arquivo processado (JSON, MD, TXT)."""
    intim = db.query(Intimacao).filter(Intimacao.id == intimacao_id).first()
    if not intim:
        raise HTTPException(status_code=404, detail="Intimação não encontrada")

    paths = {
        "json": intim.json_path,
        "md": intim.md_path,
        "txt": intim.txt_path,
        "pdf": intim.pdf_path,
    }

    caminho = paths.get(tipo)
    if not caminho or not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail=f"Arquivo {tipo} não encontrado")

    if tipo == "json":
        with open(caminho, "r", encoding="utf-8") as f:
            return json_lib.load(f)

    if tipo in ("md", "txt"):
        with open(caminho, "r", encoding="utf-8") as f:
            return {"conteudo": f.read(), "tipo": tipo}

    if tipo == "pdf":
        return FileResponse(caminho, media_type="application/pdf")

    raise HTTPException(status_code=400, detail="Tipo de arquivo inválido")
