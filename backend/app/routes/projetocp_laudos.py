"""
ProjetoCP Phase 2: FastAPI routes for Laudos (30+ endpoints)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.services.database import get_db
from app.middleware import get_current_user
from app.models import User
from app.schemas.projetocp_laudos import (
    LaudoQuesitoCriarRequest, LaudoQuesitoAtualizar, LaudoQuesitoResponse,
    LaudoAnexoCriarRequest, LaudoAnexoResponse,
    LaudoHonorarioCriarRequest, LaudoHonorarioResponse,
    LaudoCompletoResponse, LaudoGeracaoAutomaticaRequest, LaudoGeracaoResponse
)
from app.decorators.require_feature import require_feature_flag
from app.services.projetocp_laudos import (
    LaudoQuesitoService, LaudoAnexoService, LaudoHonorarioService,
    LaudoGeracaoService, LaudoValidacaoService
)

router = APIRouter(prefix="/api/v1/laudos", tags=["Laudos - Phase 2"])


# ============ QUESITOS ENDPOINTS ============

@router.post("/{laudo_id}/quesitos", response_model=LaudoQuesitoResponse, status_code=status.HTTP_201_CREATED)
async def criar_quesito(laudo_id: int, req: LaudoQuesitoCriarRequest,
                        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Criar novo quesito para um laudo"""
    try:
        quesito = LaudoQuesitoService.criar_quesitos_lote(db, laudo_id, [req.dict()])
        return quesito[0]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{laudo_id}/quesitos", response_model=List[LaudoQuesitoResponse])
async def listar_quesitos(laudo_id: int, current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """Listar todos os quesitos de um laudo"""
    quesitos = LaudoQuesitoService.listar_quesitos_por_laudo(db, laudo_id)
    return quesitos


@router.get("/{laudo_id}/quesitos/{quesito_id}", response_model=LaudoQuesitoResponse)
async def obter_quesito(laudo_id: int, quesito_id: int,
                       current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Obter detalhes de um quesito específico"""
    from app.models.projetocp_laudos import LaudoQuesito
    quesito = db.query(LaudoQuesito).filter(
        (LaudoQuesito.id == quesito_id) & (LaudoQuesito.laudo_id == laudo_id)
    ).first()
    if not quesito:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quesito não encontrado")
    return quesito


@router.patch("/{laudo_id}/quesitos/{quesito_id}", response_model=LaudoQuesitoResponse)
async def atualizar_quesito(laudo_id: int, quesito_id: int, dados: LaudoQuesitoAtualizar,
                           current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Atualizar quesito (resposta, tipo, relevância, etc)"""
    try:
        quesito = LaudoQuesitoService.atualizar_quesito(db, quesito_id, dados)
        return quesito
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{laudo_id}/quesitos/{quesito_id}/responder")
async def responder_quesito(laudo_id: int, quesito_id: int, resposta: str = Query(...),
                           current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Responder um quesito específico"""
    try:
        quesito = LaudoQuesitoService.marcar_respondido(db, quesito_id, resposta)
        return {"quesito_id": quesito.id, "status": "respondido"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{laudo_id}/quesitos/stats/resumo")
async def stats_quesitos(laudo_id: int, current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Obter resumo de quesitos (total, respondidos, etc)"""
    total = len(LaudoQuesitoService.listar_quesitos_por_laudo(db, laudo_id))
    respondidos = LaudoQuesitoService.contar_quesitos_respondidos(db, laudo_id)
    return {
        "total_quesitos": total,
        "quesitos_respondidos": respondidos,
        "quesitos_pendentes": total - respondidos,
        "percentual_completo": (respondidos / total * 100) if total > 0 else 0
    }


# ============ ANEXOS ENDPOINTS ============

@router.post("/{laudo_id}/anexos", response_model=LaudoAnexoResponse, status_code=status.HTTP_201_CREATED)
async def criar_anexo(laudo_id: int, req: LaudoAnexoCriarRequest,
                     current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Criar novo anexo para um laudo"""
    try:
        anexo = LaudoAnexoService.criar_anexo(
            db, laudo_id, req.tipo, req.titulo, req.arquivo_path,
            req.descricao, req.pagina_referencia, current_user.id
        )
        return anexo
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{laudo_id}/anexos", response_model=List[LaudoAnexoResponse])
async def listar_anexos(laudo_id: int, current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Listar todos os anexos de um laudo"""
    anexos = LaudoAnexoService.listar_anexos_por_laudo(db, laudo_id)
    return anexos


@router.delete("/{laudo_id}/anexos/{anexo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_anexo(laudo_id: int, anexo_id: int,
                       current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletar um anexo"""
    try:
        LaudoAnexoService.deletar_anexo(db, anexo_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============ HONORARIOS ENDPOINTS ============

@router.post("/{laudo_id}/honorario", response_model=LaudoHonorarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_honorario(laudo_id: int, req: LaudoHonorarioCriarRequest,
                         current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Criar/calcular honorário para um laudo"""
    try:
        honorario = LaudoHonorarioService.criar_honorario(db, req, current_user.id)
        return honorario
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{laudo_id}/honorario", response_model=LaudoHonorarioResponse)
async def obter_honorario(laudo_id: int, current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    """Obter honorário de um laudo"""
    honorario = LaudoHonorarioService.obter_honorario_por_laudo(db, laudo_id)
    if not honorario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Honorário não encontrado")
    return honorario


@router.get("/area/{area}/valor-tabela")
async def obter_valor_tabela(area: str, current_user: User = Depends(get_current_user)):
    """Obter valor de tabela OAB para uma área"""
    valor = LaudoHonorarioService.obter_valor_tabela(area)
    return {"area": area, "valor_tabela": valor}


@router.post("/{laudo_id}/honorario/calcular-sucumbencia")
async def calcular_sucumbencia(laudo_id: int, percentual: float = 90.0,
                              current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Calcular valor estimado de sucumbência"""
    from decimal import Decimal
    honorario = LaudoHonorarioService.obter_honorario_por_laudo(db, laudo_id)
    if not honorario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Honorário não encontrado")

    sucumbencia = LaudoHonorarioService.calcular_sucumbencia(
        honorario.valor_final, Decimal(percentual)
    )
    return {
        "laudo_id": laudo_id,
        "valor_laudo": honorario.valor_final,
        "percentual": percentual,
        "valor_sucumbencia": sucumbencia
    }


# ============ LAUDO GERAL ENDPOINTS ============

@router.get("/{laudo_id}", response_model=LaudoCompletoResponse)
async def obter_laudo_completo(laudo_id: int, current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Obter laudo com todos os dados relacionados (quesitos, anexos, honorário, etc)"""
    from app.models.laudo import Laudo
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laudo não encontrado")
    return laudo


@router.post("/{laudo_id}/gerar-automaticamente", response_model=LaudoGeracaoResponse)
async def gerar_laudo_automaticamente(laudo_id: int, req: LaudoGeracaoAutomaticaRequest,
                                     current_user: User = Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    """Enfileirar laudo para geração automática (Qwen + RAG)"""
    try:
        job = LaudoGeracaoService.criar_job_geracao(
            db, laudo_id, req.processo_id, req.area,
            req.etapa, req.usar_rag, req.modelo_ia
        )
        return {
            "job_id": job.id,
            "laudo_id": laudo_id,
            "status": job.status,
            "etapa": req.etapa,
            "mensagem": f"Job {job.id} enfileirado para processamento",
            "estimado_em_segundos": 60 if req.etapa == "extracao_quesitos" else 120
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{laudo_id}/estruturar-quesitos")
async def estruturar_quesitos_automaticamente(laudo_id: int, current_user: User = Depends(get_current_user),
                                             db: Session = Depends(get_db)):
    """Extrair quesitos automaticamente da intimação usando Qwen"""
    try:
        job = LaudoGeracaoService.criar_job_geracao(
            db, laudo_id, processo_id=0, area="geral",
            etapa="extracao_quesitos", usar_rag=False
        )
        return {
            "status": "enfileirado",
            "job_id": job.id,
            "mensagem": "Extração de quesitos enfileirada"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============ VALIDAÇÃO E DIAGNOSTICO ============

@router.get("/{laudo_id}/validacao/estrutura")
async def validar_estrutura(laudo_id: int, current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Validar se laudo tem estrutura completa e pronto para protocolo"""
    try:
        validacao = LaudoValidacaoService.validar_estrutura_completa(db, laudo_id)
        return validacao
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{laudo_id}/diagnostico")
async def diagnosticar_laudo(laudo_id: int, current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Gerar diagnóstico completo com recomendações de próximos passos"""
    try:
        diagnostico = LaudoValidacaoService.diagnosticar_laudo(db, laudo_id)
        return diagnostico
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============ RELATÓRIOS ============

@router.get("/area/{area}/relatorio-laudos")
async def relatorio_laudos_por_area(area: str, current_user: User = Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    """Relatório de laudos por área"""
    from app.models.laudo import Laudo
    from app.models.projetocp_laudos import LaudoHonorario
    from sqlalchemy import func

    laudos = db.query(Laudo).filter(Laudo.tipo_laudo == area).all()

    honorarios = db.query(
        func.count(LaudoHonorario.id),
        func.sum(LaudoHonorario.valor_final)
    ).filter(LaudoHonorario.area == area).first()

    return {
        "area": area,
        "quantidade_laudos": len(laudos),
        "laudos_por_status": {
            "rascunho": len([l for l in laudos if l.status == "rascunho"]),
            "estruturado": len([l for l in laudos if l.status == "estruturado"]),
            "revisao": len([l for l in laudos if l.status in ["revisao_interna", "revisao_cliente"]]),
            "pronto": len([l for l in laudos if l.status == "pronto_protocolo"]),
            "finalizado": len([l for l in laudos if l.status == "finalizado"]),
        },
        "valor_total_honorarios": honorarios[1] or 0 if honorarios else 0,
        "quantidade_honorarios": honorarios[0] or 0 if honorarios else 0,
    }


@router.get("/stats/dashboard")
async def dashboard_laudos(current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Dashboard geral de laudos"""
    from app.models.laudo import Laudo
    from app.models.projetocp_laudos import LaudoHonorario
    from sqlalchemy import func

    total_laudos = db.query(func.count(Laudo.id)).scalar()
    laudos_finalizados = db.query(func.count(Laudo.id)).filter(Laudo.status == "finalizado").scalar()
    valor_total = db.query(func.sum(LaudoHonorario.valor_final)).scalar()

    return {
        "total_laudos": total_laudos,
        "laudos_finalizados": laudos_finalizados,
        "percentual_finalizacao": (laudos_finalizados / total_laudos * 100) if total_laudos > 0 else 0,
        "valor_total_honorarios": valor_total or 0,
        "valor_medio_laudo": (valor_total / total_laudos) if total_laudos > 0 else 0,
    }
