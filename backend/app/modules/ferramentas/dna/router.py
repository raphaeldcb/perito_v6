"""
DNA Module Router — FastAPI endpoints for DNA analysis.

Endpoints:
- GET /tipos-parentesco — Static DNA relationship types
- GET /enquadramentos — Static DNA frameworks
- GET /processos/{id}/valor-total — Calculate total DNA value
- GET /processos/{id}/sumario — Get DNA summary for process
- CRUD endpoints for participants and enquadramentos
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.services.database import get_db
from app.models import ParticipanteDNA, EnquadramentoDNA, Processo
from app.middleware.auth import get_current_user
from app.decorators.require_feature import require_feature_flag

from . import schemas, service

router = APIRouter(prefix="/api/v1/dna", tags=["DNA"])


# ============= DYNAMIC ENDPOINTS =============

@router.get("/tipos-parentesco")
async def get_tipos_parentesco():
    """Retorna lista de tipos de parentesco DNA para dropdown (público)."""
    return service.get_tipos_parentesco()


@router.get("/processos/{processo_id}/valor-total")
async def calcular_valor_dna(
    processo_id: int,
    db: Session = Depends(get_db)
):
    """Calcula valor total DNA (judicial + particular) para integração financeira."""
    resultado = service.calcular_valor_dna(processo_id, db)
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    return resultado


@router.get("/processos/{processo_id}/sumario")
async def sumario_dna(
    processo_id: int,
    db: Session = Depends(get_db)
):
    """Retorna sumário DNA para exibição no andamento do processo."""
    resultado = service.sumario_dna(processo_id, db)
    if "error" in resultado:
        raise HTTPException(status_code=404, detail=resultado["error"])
    return resultado


@router.get("/enquadramentos")
async def get_enquadramentos():
    """Retorna lista de enquadramentos DNA para dropdown."""
    return service.get_enquadramentos()


# ============= PARTICIPANTES DNA =============

@router.post("/processos/{processo_id}/participantes", response_model=schemas.ParticipanteDNAResponse)
async def criar_participante_dna(
    processo_id: int,
    participante: schemas.ParticipanteDNACreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cria um novo participante DNA para um processo."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    db_participante = ParticipanteDNA(
        processo_id=processo_id,
        tipo=participante.tipo,
        nome=participante.nome,
        requerente=participante.requerente,
        requerido=participante.requerido,
    )
    db.add(db_participante)
    db.commit()
    db.refresh(db_participante)
    return db_participante


@router.get("/processos/{processo_id}/participantes", response_model=List[schemas.ParticipanteDNAResponse])
async def listar_participantes_dna(
    processo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todos os participantes DNA de um processo."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    participantes = db.query(ParticipanteDNA).filter(
        ParticipanteDNA.processo_id == processo_id
    ).all()
    return participantes


@router.get("/participantes/{participante_id}", response_model=schemas.ParticipanteDNAResponse)
async def obter_participante_dna(
    participante_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Obtém um participante DNA específico."""
    participante = db.query(ParticipanteDNA).filter(
        ParticipanteDNA.id == participante_id
    ).first()
    if not participante:
        raise HTTPException(status_code=404, detail="Participante DNA não encontrado")
    return participante


@router.put("/participantes/{participante_id}", response_model=schemas.ParticipanteDNAResponse)
async def atualizar_participante_dna(
    participante_id: int,
    participante: schemas.ParticipanteDNAUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Atualiza um participante DNA."""
    db_participante = db.query(ParticipanteDNA).filter(
        ParticipanteDNA.id == participante_id
    ).first()
    if not db_participante:
        raise HTTPException(status_code=404, detail="Participante DNA não encontrado")

    for key, value in participante.dict(exclude_unset=True).items():
        setattr(db_participante, key, value)

    db.commit()
    db.refresh(db_participante)
    return db_participante


@router.delete("/participantes/{participante_id}")
async def deletar_participante_dna(
    participante_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Deleta um participante DNA."""
    db_participante = db.query(ParticipanteDNA).filter(
        ParticipanteDNA.id == participante_id
    ).first()
    if not db_participante:
        raise HTTPException(status_code=404, detail="Participante DNA não encontrado")

    db.delete(db_participante)
    db.commit()
    return {"mensagem": "Participante DNA deletado"}


# ============= ENQUADRAMENTOS DNA =============

@router.post("/processos/{processo_id}/enquadramentos", response_model=schemas.EnquadramentoDNAResponse)
async def criar_enquadramento_dna(
    processo_id: int,
    enquadramento: schemas.EnquadramentoDNACreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cria um novo enquadramento DNA para um processo."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    db_enquadramento = EnquadramentoDNA(
        processo_id=processo_id,
        codigo=enquadramento.codigo,
        descricao=enquadramento.descricao,
        valor_particular=enquadramento.valor_particular,
        valor_judicial=enquadramento.valor_judicial,
        resultado=enquadramento.resultado,
        probabilidade=enquadramento.probabilidade,
        observacoes=enquadramento.observacoes,
    )
    db.add(db_enquadramento)
    db.commit()
    db.refresh(db_enquadramento)
    return db_enquadramento


@router.get("/processos/{processo_id}/enquadramentos", response_model=List[schemas.EnquadramentoDNAResponse])
async def listar_enquadramentos_dna(
    processo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Lista todos os enquadramentos DNA de um processo."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    enquadramentos = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.processo_id == processo_id
    ).all()
    return enquadramentos


@router.get("/enquadramentos/{enquadramento_id}", response_model=schemas.EnquadramentoDNAResponse)
async def obter_enquadramento_dna(
    enquadramento_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Obtém um enquadramento DNA específico."""
    enquadramento = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.id == enquadramento_id
    ).first()
    if not enquadramento:
        raise HTTPException(status_code=404, detail="Enquadramento DNA não encontrado")
    return enquadramento


@router.put("/enquadramentos/{enquadramento_id}", response_model=schemas.EnquadramentoDNAResponse)
async def atualizar_enquadramento_dna(
    enquadramento_id: int,
    enquadramento: schemas.EnquadramentoDNAUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Atualiza um enquadramento DNA."""
    db_enquadramento = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.id == enquadramento_id
    ).first()
    if not db_enquadramento:
        raise HTTPException(status_code=404, detail="Enquadramento DNA não encontrado")

    for key, value in enquadramento.dict(exclude_unset=True).items():
        setattr(db_enquadramento, key, value)

    db.commit()
    db.refresh(db_enquadramento)
    return db_enquadramento


@router.delete("/enquadramentos/{enquadramento_id}")
async def deletar_enquadramento_dna(
    enquadramento_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Deleta um enquadramento DNA."""
    db_enquadramento = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.id == enquadramento_id
    ).first()
    if not db_enquadramento:
        raise HTTPException(status_code=404, detail="Enquadramento DNA não encontrado")

    db.delete(db_enquadramento)
    db.commit()
    return {"mensagem": "Enquadramento DNA deletado"}
