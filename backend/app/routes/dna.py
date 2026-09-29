from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.services.database import get_db
from app.models import ParticipanteDNA, EnquadramentoDNA, Processo, TipoParentescoDNA, ResultadoDNA
from app.schemas.dna import (
    ParticipanteDNACreate, ParticipanteDNAResponse, ParticipanteDNAUpdate,
    EnquadramentoDNACreate, EnquadramentoDNAResponse, EnquadramentoDNAUpdate
)
from app.middleware.auth import get_current_user
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/dna", tags=["DNA"])

# ============= ENDPOINTS DINÂMICOS =============

@router.get("/tipos-parentesco")
async def get_tipos_parentesco():
    """Retorna lista de tipos de parentesco DNA para dropdown (público)."""
    return {
        "tipos": [
            {"id": "CRI", "label": "Criança/Investigante"},
            {"id": "MA1", "label": "Mãe"},
            {"id": "MA2", "label": "Mãe dos SMIs"},
            {"id": "SP1", "label": "Suposto Pai 1"},
            {"id": "SP2", "label": "Suposto Pai 2"},
            {"id": "SP3", "label": "Suposto Pai 3"},
            {"id": "SMI1", "label": "Suposto Meio-Irmão 1 (com MA2)"},
            {"id": "SMI2", "label": "Suposto Meio-Irmão 2 (com MA2)"},
            {"id": "SMI3", "label": "Suposto Meio-Irmão 3 (com MA2)"},
            {"id": "ST1", "label": "Suposto Tio Paterno 1"},
            {"id": "ST2", "label": "Suposto Tio Paterno 2"},
            {"id": "ST3", "label": "Suposto Tio Paterno 3"},
            {"id": "AGM", "label": "Suposto Avó Materna"},
            {"id": "AGF", "label": "Suposto Avô Paterno"},
            {"id": "OUTRO", "label": "Outro"},
        ]
    }

@router.get("/processos/{processo_id}/valor-total")
async def calcular_valor_dna(
    processo_id: int,
    db: Session = Depends(get_db)
):
    """Calcula valor total DNA (judicial + particular) para integração financeira."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    enquadramentos = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.processo_id == processo_id
    ).all()

    valor_total_judicial = sum(e.valor_judicial or 0 for e in enquadramentos)
    valor_total_particular = sum(e.valor_particular or 0 for e in enquadramentos)

    return {
        "processo_id": processo_id,
        "quantidade_enquadramentos": len(enquadramentos),
        "valor_judicial": valor_total_judicial,
        "valor_particular": valor_total_particular,
        "enquadramentos": [
            {
                "codigo": e.codigo,
                "descricao": e.descricao,
                "valor_judicial": e.valor_judicial,
                "valor_particular": e.valor_particular,
                "resultado": e.resultado,
                "probabilidade": e.probabilidade
            }
            for e in enquadramentos
        ]
    }

@router.get("/processos/{processo_id}/sumario")
async def sumario_dna(
    processo_id: int,
    db: Session = Depends(get_db)
):
    """Retorna sumário DNA para exibição no andamento do processo."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    participantes = db.query(ParticipanteDNA).filter(
        ParticipanteDNA.processo_id == processo_id
    ).all()

    enquadramentos = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.processo_id == processo_id
    ).all()

    requerentes = [p.nome for p in participantes if p.requerente]
    requeridos = [p.nome for p in participantes if p.requerido]

    resultado_final = None
    if enquadramentos:
        resultado_final = enquadramentos[0].resultado
        if resultado_final == "INCLUSÃO" and enquadramentos[0].probabilidade:
            resultado_final = f"INCLUSÃO ({enquadramentos[0].probabilidade}%)"

    return {
        "processo_id": processo_id,
        "total_participantes": len(participantes),
        "requerentes": requerentes,
        "requeridos": requeridos,
        "enquadramentos_selecionados": len(enquadramentos),
        "resultado_dna": resultado_final,
        "status": "Aguardando resultado" if not resultado_final else "Resultado disponível"
    }

@router.get("/enquadramentos")
async def get_enquadramentos():
    """Retorna lista de enquadramentos DNA para dropdown."""
    return {
        "enquadramentos": [
            # PATERNIDADE DIRETA
            {
                "id": "PD0101",
                "codigo": "PD0101",
                "descricao": "Mãe, criança e suposto pai",
                "categoria": "Paternidade Direta",
                "valor_particular": 800.00,
                "valor_judicial": 600.00,
            },
            {
                "id": "PD0201",
                "codigo": "PD0201",
                "descricao": "Criança e suposto pai",
                "categoria": "Paternidade Direta",
                "valor_particular": 800.00,
                "valor_judicial": 600.00,
            },
            # RECONSTRUÇÃO DIRETA
            {
                "id": "RD0301",
                "codigo": "RD0301",
                "descricao": "Mãe, criança e supostos avós",
                "categoria": "Reconstrução Direta",
                "valor_particular": 1500.00,
                "valor_judicial": 1200.00,
            },
            {
                "id": "RD0302",
                "codigo": "RD0302",
                "descricao": "Criança e supostos avós",
                "categoria": "Reconstrução Direta",
                "valor_particular": 2100.00,
                "valor_judicial": 1800.00,
            },
            {
                "id": "RD0501",
                "codigo": "RD0501",
                "descricao": "Mãe, criança e 3 supostos meios-irmãos com MA2",
                "categoria": "Reconstrução Direta",
                "valor_particular": 2700.00,
                "valor_judicial": 2400.00,
            },
            {
                "id": "RD0502",
                "codigo": "RD0502",
                "descricao": "Mãe, criança e 2 supostos meios-irmãos com MA2",
                "categoria": "Reconstrução Direta",
                "valor_particular": 3200.00,
                "valor_judicial": 3000.00,
            },
            {
                "id": "RD0503",
                "codigo": "RD0503",
                "descricao": "Mãe, criança e 1 suposto meio-irmão com MA2",
                "categoria": "Reconstrução Direta",
                "valor_particular": 3800.00,
                "valor_judicial": 3200.00,
            },
            # RECONSTRUÇÃO INDIRETA
            {
                "id": "RI0401",
                "codigo": "RI0401",
                "descricao": "Mãe, criança e 3 supostos tios paternos",
                "categoria": "Reconstrução Indireta",
                "valor_particular": 2700.00,
                "valor_judicial": 2400.00,
            },
            {
                "id": "RI0402",
                "codigo": "RI0402",
                "descricao": "Mãe, criança e 2 supostos tios paternos",
                "categoria": "Reconstrução Indireta",
                "valor_particular": 3200.00,
                "valor_judicial": 3000.00,
            },
            {
                "id": "RI0403",
                "codigo": "RI0403",
                "descricao": "Mãe, criança e 1 suposto tio paterno com 1 dos avós",
                "categoria": "Reconstrução Indireta",
                "valor_particular": 3800.00,
                "valor_judicial": 3200.00,
            },
        ]
    }

# ============= PARTICIPANTES DNA =============

@router.post("/processos/{processo_id}/participantes", response_model=ParticipanteDNAResponse)
async def criar_participante_dna(
    processo_id: int,
    participante: ParticipanteDNACreate,
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

@router.get("/processos/{processo_id}/participantes", response_model=List[ParticipanteDNAResponse])
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

@router.get("/participantes/{participante_id}", response_model=ParticipanteDNAResponse)
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

@router.put("/participantes/{participante_id}", response_model=ParticipanteDNAResponse)
async def atualizar_participante_dna(
    participante_id: int,
    participante: ParticipanteDNAUpdate,
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

@router.post("/processos/{processo_id}/enquadramentos", response_model=EnquadramentoDNAResponse)
async def criar_enquadramento_dna(
    processo_id: int,
    enquadramento: EnquadramentoDNACreate,
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

@router.get("/processos/{processo_id}/enquadramentos", response_model=List[EnquadramentoDNAResponse])
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

@router.get("/enquadramentos/{enquadramento_id}", response_model=EnquadramentoDNAResponse)
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

@router.put("/enquadramentos/{enquadramento_id}", response_model=EnquadramentoDNAResponse)
async def atualizar_enquadramento_dna(
    enquadramento_id: int,
    enquadramento: EnquadramentoDNAUpdate,
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
