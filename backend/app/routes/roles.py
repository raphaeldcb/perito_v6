from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import RoleCreate, RoleRead
from app.models import Role, User
from app.services import get_db
from app.middleware import get_current_user

router = APIRouter()


@router.get("", response_model=list[RoleRead])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can list roles")
    roles = db.query(Role).all()
    return roles


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view roles")
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post("", response_model=RoleRead)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create roles")
    if db.query(Role).filter(Role.name == role_data.name).first():
        raise HTTPException(status_code=400, detail="Role already exists")
    new_role = Role(**role_data.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role
