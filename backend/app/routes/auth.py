from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.services import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_db,
)
from app.models import User
from app.middleware import get_current_user
from app.middleware.rate_limiting import limiter

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # 5 login attempts per IP per minute (brute force protection)
async def login(request: Request, login_request: LoginRequest, db: Session = Depends(get_db)):
    # Aceita login por email completo OU só usuário (parte antes do @).
    # Ex.: "admin" casa com "admin@ipcms.com.br". Não quebra o login por email.
    login_txt = login_request.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == login_txt).first()
    if not user and "@" not in login_txt:
        user = db.query(User).filter(func.lower(User.email).like(f"{login_txt}@%")).first()

    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=15 * 60,
    )


@router.get("/me", response_model=None)
async def get_me(user = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.name,
        "is_active": user.is_active,
    }


@router.post("/logout", response_model=None)
async def logout(user = Depends(get_current_user)):
    return {"message": "Logged out successfully"}


class TrocarSenha(BaseModel):
    senha_atual: str
    nova_senha: str


@router.post("/trocar-senha", response_model=None)
async def trocar_senha(
    payload: TrocarSenha,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    from app.services import hash_password
    if not verify_password(payload.senha_atual, user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(payload.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter ao menos 6 caracteres")
    user.hashed_password = hash_password(payload.nova_senha)
    db.commit()
    return {"ok": True}
