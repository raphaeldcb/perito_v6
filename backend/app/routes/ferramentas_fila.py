from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.fila_intimacoes import FilaIntimacao, FilaStatus
from app.decorators.require_feature import require_feature_flag
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/ferramentas/fila", tags=["fila"])

class FilaCreate(BaseModel):
    laudo_id: int
    oficio_path: Optional[str] = None

class FilaUpdate(BaseModel):
    status: FilaStatus
    oficio_path: Optional[str] = None

class FilaResponse(BaseModel):
    id: int
    laudo_id: int
    status: FilaStatus
    oficio_path: Optional[str]
    criado_em: str
    criado_por: int
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[FilaResponse])
async def listar_fila(
    status: Optional[FilaStatus] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """Listar fila com filtro opcional por status"""
    query = db.query(FilaIntimacao)
    if status:
        query = query.filter(FilaIntimacao.status == status)
    return query.offset(skip).limit(limit).all()

@router.post("", response_model=FilaResponse, status_code=201)
async def criar_fila(
    fila: FilaCreate,
    db: Session = Depends(get_db)
):
    """Criar novo item na fila"""
    novo = FilaIntimacao(
        laudo_id=fila.laudo_id,
        oficio_path=fila.oficio_path,
        criado_por=1  # TODO: usar current_user
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@router.patch("/{fila_id}", response_model=FilaResponse)
async def atualizar_fila(
    fila_id: int,
    update: FilaUpdate,
    db: Session = Depends(get_db)
):
    """Atualizar status de item na fila"""
    item = db.query(FilaIntimacao).filter(FilaIntimacao.id == fila_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Fila não encontrada")
    
    item.status = update.status
    if update.oficio_path:
        item.oficio_path = update.oficio_path
    
    db.commit()
    db.refresh(item)
    return item

@router.get("/{fila_id}", response_model=FilaResponse)
async def obter_fila(
    fila_id: int,
    db: Session = Depends(get_db)
):
    """Obter item específico da fila"""
    item = db.query(FilaIntimacao).filter(FilaIntimacao.id == fila_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Fila não encontrada")
    return item
