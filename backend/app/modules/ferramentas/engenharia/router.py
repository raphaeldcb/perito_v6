"""Engenharia — vistorias de campo (schema-driven, PWA offline).

Modelos (templates configuráveis) + Vistorias (preenchimentos). O upsert por
`uuid_offline` permite que o dispositivo crie a vistoria offline e sincronize
depois sem duplicar.

Fase 2: PDF + assinatura digital + laudo Qwen + offline PWA.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User
from app.services import get_db
from app.decorators.require_feature import require_feature_flag

from . import service
from . import schemas

router = APIRouter(prefix="/api/v1/engenharia", tags=["engenharia"])


# ================================================================ MODELOS
@router.get("/modelos", response_model=list[schemas.ModeloVistoriaResponse])
async def listar_modelos(
    incluir_inativos: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lista todos os modelos de vistoria."""
    return service.listar_modelos(db, incluir_inativos)


@router.get("/modelos/{modelo_id}", response_model=schemas.ModeloVistoriaDetailResponse)
async def obter_modelo(
    modelo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Obtém um modelo específico com seu schema."""
    modelo = service.obter_modelo(db, modelo_id)
    if not modelo:
        raise HTTPException(404, "Modelo não encontrado")
    return modelo


@router.post("/modelos", response_model=schemas.ModeloVistoriaCreateResponse)
async def criar_modelo(
    body: schemas.ModeloVistoriaCreateRequest = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cria novo modelo de vistoria."""
    return service.criar_modelo(db, body.model_dump())


@router.put("/modelos/{modelo_id}")
async def atualizar_modelo(
    modelo_id: int,
    body: schemas.ModeloVistoriaUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Atualiza um modelo de vistoria."""
    resultado = service.atualizar_modelo(db, modelo_id, body.model_dump(exclude_none=True))
    if not resultado:
        raise HTTPException(404, "Modelo não encontrado")
    return resultado


# ============================================================= VISTORIAS
@router.get("/vistorias", response_model=list[schemas.VistoriaResponse])
async def listar_vistorias(
    processo_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lista todas as vistorias com filtros opcionais."""
    return service.listar_vistorias(db, processo_id, status)


@router.get("/vistorias/{vistoria_id}", response_model=schemas.VistoriaDetailResponse)
async def obter_vistoria(
    vistoria_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Obtém uma vistoria com detalhes completos."""
    vistoria = service.obter_vistoria(db, vistoria_id)
    if not vistoria:
        raise HTTPException(404, "Vistoria não encontrada")
    return vistoria


@router.post("/vistorias", response_model=schemas.VistoriaResponse)
async def upsert_vistoria(
    body: schemas.VistoriaCreateRequest = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cria OU atualiza (por uuid_offline) — base da sincronização offline."""
    resultado = service.upsert_vistoria(db, user, body.model_dump())
    if not resultado:
        raise HTTPException(400, "modelo_id inválido")
    return resultado


@router.post("/vistorias/{vistoria_id}/enviar", response_model=schemas.VistoriaEnviarResponse)
async def enviar_vistoria(
    vistoria_id: int,
    body: schemas.VistoriaEnviarRequest = Body(default=schemas.VistoriaEnviarRequest()),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Finaliza a vistoria: marca enviada e (opcional) vincula ao processo.
    Fase 2: gera PDF automático + rascunho de laudo."""
    resultado = service.enviar_vistoria(db, vistoria_id, body.processo_id)
    if not resultado:
        raise HTTPException(404, "Vistoria não encontrada")
    return resultado


# ====== FASE 2: PDF, LAUDO, ASSINATURA

@router.get("/vistorias/{vistoria_id}/pdf")
async def download_pdf_vistoria(
    vistoria_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download do PDF da vistoria (pronto para assinatura digital)."""
    pdf_path = service.obter_ou_gerar_pdf(db, vistoria_id)
    if not pdf_path:
        raise HTTPException(404, "Arquivo PDF não encontrado")

    vistoria = db.query(Vistoria).get(vistoria_id)
    if not vistoria:
        raise HTTPException(404, "Vistoria não encontrada")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"vistoria_{vistoria_id}_{vistoria.modelo.nome.replace(' ', '_')}.pdf",
    )


@router.post("/vistorias/{vistoria_id}/gerar-laudo")
async def gerar_laudo(
    vistoria_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Gera parecer técnico automático com Qwen (async, Fase 2)."""
    resultado = service.gerar_laudo(db, vistoria_id)
    if not resultado:
        raise HTTPException(500, "Erro ao gerar laudo")
    return resultado


@router.get("/vistorias/{vistoria_id}/laudo", response_model=schemas.LaudoVistoriaResponse)
async def obter_laudo(
    vistoria_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retorna o laudo rascunho da vistoria (se gerado)."""
    resultado = service.obter_laudo(db, vistoria_id)
    if not resultado:
        raise HTTPException(404, "Vistoria não encontrada")
    return resultado


@router.post("/vistorias/{vistoria_id}/assinar")
async def registrar_assinatura_vistoria(
    vistoria_id: int,
    body: schemas.VistoriaAssinaturaPdfRequest = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Registra assinatura digital (hash/certificado) no PDF."""
    resultado = service.registrar_assinatura(db, vistoria_id, body.model_dump())
    if not resultado:
        raise HTTPException(400, "Vistoria não tem PDF gerado")
    return resultado


@router.post("/vistorias/{vistoria_id}/fotos", response_model=schemas.VistoriaFotoResponse)
async def adicionar_foto_vistoria(
    vistoria_id: int,
    body: schemas.VistoriaFotoCreateRequest = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Adiciona foto (base64) à vistoria. Permite sincronização offline."""
    resultado = service.adicionar_foto(db, vistoria_id, body.model_dump())
    if not resultado:
        raise HTTPException(500, "Erro ao adicionar foto")
    return resultado
