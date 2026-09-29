"""Portal do coletador (acesso restrito) + gestão pelo admin.

Coletador loga por CPF, recebe JWT com subject 'col:<id>' e enxerga APENAS o
próprio portal: comprovantes de pagamento, termo de autorização (preenchível/
exportável), contrato, vídeo e documentos. Upload de documentos habilitado.
"""
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.middleware import get_current_user
from app.models import User, Coletador, DocumentoColetador, Empresa
from app.services import get_db, hash_password, verify_password, create_access_token, decode_token
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/coletador", tags=["coletador"])
security = HTTPBearer()

TIPOS_DOC = ["comprovante", "termo_autorizacao", "contrato", "video", "outro"]


# ---- Auth do coletador -----------------------------------------------------
class ColetadorLogin(BaseModel):
    cpf: str
    senha: str


class PrimeiroAcesso(BaseModel):
    nova_senha: str
    email_pessoal: str | None = None
    celular: str | None = None
    pix: str | None = None
    conta_bancaria: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    cep: str | None = None


def _limpar_cpf(cpf: str) -> str:
    import re
    return re.sub(r"\D", "", cpf or "")


def get_current_coletador(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Coletador:
    payload = decode_token(credentials.credentials)
    sub = (payload or {}).get("sub", "")
    if not payload or not sub.startswith("col:"):
        raise HTTPException(status_code=401, detail="Token de coletador inválido")
    coletador = db.query(Coletador).filter(Coletador.id == int(sub[4:])).first()
    if not coletador or not coletador.ativo:
        raise HTTPException(status_code=401, detail="Coletador não encontrado ou inativo")
    return coletador


@router.post("/login")
async def login_coletador(payload: ColetadorLogin, db: Session = Depends(get_db)):
    cpf = _limpar_cpf(payload.cpf)
    coletador = db.query(Coletador).filter(Coletador.cpf == cpf).first()
    if not coletador or not verify_password(payload.senha, coletador.hashed_password):
        raise HTTPException(status_code=401, detail="CPF ou senha inválidos")
    if not coletador.ativo:
        raise HTTPException(status_code=403, detail="Coletador inativo")

    token = create_access_token({"sub": f"col:{coletador.id}"}, expires_delta=timedelta(hours=8))
    return {
        "access_token": token,
        "primeiro_acesso": coletador.primeiro_acesso,
        "nome": coletador.nome_completo,
    }


@router.post("/primeiro-acesso")
async def primeiro_acesso(
    payload: PrimeiroAcesso,
    db: Session = Depends(get_db),
    coletador: Coletador = Depends(get_current_coletador),
):
    if len(payload.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter ao menos 6 caracteres")
    coletador.hashed_password = hash_password(payload.nova_senha)
    for campo in ["email_pessoal", "celular", "pix", "conta_bancaria", "endereco", "cidade", "cep"]:
        valor = getattr(payload, campo)
        if valor:
            setattr(coletador, campo, valor.strip())
    coletador.primeiro_acesso = False
    db.commit()
    return {"ok": True}


def _doc_json(d: DocumentoColetador) -> dict:
    return {
        "id": d.id, "tipo": d.tipo, "titulo": d.titulo,
        "referencia": d.referencia, "valor": float(d.valor) if d.valor is not None else None,
        "tem_arquivo": bool(d.arquivo_path),
        "dados_formulario": d.dados_formulario,
        "criado_em": d.created_at.isoformat() if d.created_at else None,
    }


@router.get("/me")
async def meu_portal(
    db: Session = Depends(get_db),
    coletador: Coletador = Depends(get_current_coletador),
):
    docs = db.query(DocumentoColetador).filter(
        DocumentoColetador.coletador_id == coletador.id
    ).order_by(DocumentoColetador.created_at.desc()).all()
    return {
        "coletador": {
            "nome": coletador.nome_completo, "apelido": coletador.apelido,
            "cpf": coletador.cpf, "pix": coletador.pix,
            "primeiro_acesso": coletador.primeiro_acesso,
        },
        "documentos": {
            tipo: [_doc_json(d) for d in docs if d.tipo == tipo] for tipo in TIPOS_DOC
        },
    }


@router.post("/documentos")
async def enviar_documento(
    tipo: str = Form(...),
    titulo: str = Form(""),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    coletador: Coletador = Depends(get_current_coletador),
):
    """Coletador envia um documento (ex: termo assinado, foto de comprovante)."""
    if tipo not in TIPOS_DOC:
        raise HTTPException(status_code=400, detail=f"tipo deve ser um de {TIPOS_DOC}")

    arquivo_path = None
    if file:
        base = os.path.join(settings.storage_dir, "coletadores", str(coletador.id))
        os.makedirs(base, exist_ok=True)
        arquivo_path = os.path.join(base, f"{tipo}_{file.filename}")
        with open(arquivo_path, "wb") as f:
            f.write(await file.read())

    doc = DocumentoColetador(
        coletador_id=coletador.id, tipo=tipo, titulo=titulo or file.filename if file else titulo,
        arquivo_path=arquivo_path, enviado_por_coletador=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_json(doc)


@router.get("/documentos/{doc_id}/arquivo")
async def baixar_documento(
    doc_id: int,
    db: Session = Depends(get_db),
    coletador: Coletador = Depends(get_current_coletador),
):
    """Coletador baixa um documento SEU (comprovante, contrato, vídeo...)."""
    from fastapi.responses import FileResponse
    doc = db.query(DocumentoColetador).filter(
        DocumentoColetador.id == doc_id,
        DocumentoColetador.coletador_id == coletador.id,  # só o próprio
    ).first()
    if not doc or not doc.arquivo_path or not os.path.exists(doc.arquivo_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(doc.arquivo_path, filename=os.path.basename(doc.arquivo_path))


class TermoAutorizacao(BaseModel):
    dados_formulario: dict


@router.post("/termo-autorizacao")
async def salvar_termo(
    payload: TermoAutorizacao,
    db: Session = Depends(get_db),
    coletador: Coletador = Depends(get_current_coletador),
):
    """Salva o termo de autorização de coleta preenchido (exportável a PDF depois)."""
    doc = db.query(DocumentoColetador).filter(
        DocumentoColetador.coletador_id == coletador.id,
        DocumentoColetador.tipo == "termo_autorizacao",
    ).first()
    if not doc:
        doc = DocumentoColetador(coletador_id=coletador.id, tipo="termo_autorizacao",
                                 titulo="Termo de Autorização de Coleta")
        db.add(doc)
    doc.dados_formulario = payload.dados_formulario
    db.commit()
    return {"ok": True}


# ---- Gestão pelo admin -----------------------------------------------------
def exigir_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")
    return user


@router.get("/admin/lista")
async def listar_coletadores(
    busca: str = "",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    q = db.query(Coletador)
    if busca:
        like = f"%{busca}%"
        q = q.filter((Coletador.nome_completo.ilike(like)) | (Coletador.apelido.ilike(like)) | (Coletador.cpf.ilike(like)))
    total = q.count()
    itens = q.order_by(Coletador.nome_completo).offset(skip).limit(limit).all()
    return {
        "total": total,
        "itens": [
            {"id": c.id, "nome": c.nome_completo, "apelido": c.apelido, "cpf": c.cpf,
             "empresa_id": c.empresa_id, "is_prestador": c.is_prestador, "ativo": c.ativo,
             "primeiro_acesso": c.primeiro_acesso, "pix": c.pix}
            for c in itens
        ],
    }


class ColetadorUpdate(BaseModel):
    empresa_id: int | None = None
    is_prestador: bool | None = None
    ativo: bool | None = None


@router.patch("/admin/{coletador_id}")
async def atualizar_coletador(
    coletador_id: int,
    payload: ColetadorUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    c = db.query(Coletador).filter(Coletador.id == coletador_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Coletador não encontrado")
    if payload.empresa_id is not None:
        c.empresa_id = payload.empresa_id or None
    if payload.is_prestador is not None:
        c.is_prestador = payload.is_prestador
    if payload.ativo is not None:
        c.ativo = payload.ativo
    db.commit()
    return {"ok": True}


@router.post("/admin/{coletador_id}/comprovante")
async def anexar_comprovante(
    coletador_id: int,
    referencia: str = Form(...),
    valor: float = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """Admin anexa um comprovante de pagamento ao coletador (aparece no portal dele)."""
    c = db.query(Coletador).filter(Coletador.id == coletador_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Coletador não encontrado")
    base = os.path.join(settings.storage_dir, "coletadores", str(coletador_id))
    os.makedirs(base, exist_ok=True)
    caminho = os.path.join(base, f"comprovante_{referencia}_{file.filename}")
    with open(caminho, "wb") as f:
        f.write(await file.read())
    doc = DocumentoColetador(
        coletador_id=coletador_id, tipo="comprovante",
        titulo=f"Comprovante {referencia}", referencia=referencia,
        valor=valor, arquivo_path=caminho,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_json(doc)


@router.get("/admin/empresas")
async def listar_empresas(db: Session = Depends(get_db), user: User = Depends(exigir_admin)):
    return [
        {"id": e.id, "razao_social": e.razao_social, "nome_fantasia": e.nome_fantasia,
         "cnpj": e.cnpj, "regime": e.regime_tributario}
        for e in db.query(Empresa).all()
    ]
