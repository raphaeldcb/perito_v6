from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.database import get_db
from app.services.feature_flag_service import feature_flag_service
from app.models.feature_flag import FeatureFlag
from app.middleware import get_current_user

router = APIRouter(prefix="/api/v1/admin/feature-flags", tags=["admin"])


@router.get("")
def list_flags(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    flags = db.query(FeatureFlag).all()
    return [{"id": f.id, "nome": f.nome, "ativo": f.ativo, "descricao": f.descricao} for f in flags]


@router.patch("/{feature_name}")
def toggle_flag(feature_name: str, ativo: bool, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    flag = db.query(FeatureFlag).filter(FeatureFlag.nome == feature_name).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature não encontrada")

    feature_flag_service.set_flag(feature_name, ativo, db)
    return {"nome": flag.nome, "ativo": ativo}
