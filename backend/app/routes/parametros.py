"""Parâmetros do sistema: o admin edita pela UI, o agente Mac consome via API.

Valores secretos (senhas) são mascarados no GET normal; o agente recebe
os valores reais autenticando com X-Agent-Key.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User
from app.models.parametro import Parametro
from app.routes.jobs import verificar_agente
from app.services import get_db
from app.services.caminhos import analisar_caminho, carregar_mapa
from app.middleware.rate_limiting import limiter, RATE_LIMITS

router = APIRouter(prefix="/api/v1/parametros", tags=["parametros"])

CATEGORIAS = ["credenciais", "urls", "caminhos", "valores", "sistema", "produtividade"]


class ParametroUpsert(BaseModel):
    valor: str


class ParametroCreate(BaseModel):
    chave: str
    valor: str = ""
    categoria: str = "sistema"
    descricao: str = ""
    secreto: bool = False
    tipo: str = "texto"


def exigir_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins")
    return user


def _mapa(db: Session) -> dict:
    p = db.query(Parametro).filter(Parametro.chave == "mapa_unidades_windows").first()
    return carregar_mapa(p.valor if p else "{}")


def _serializar(p: Parametro, mapa: dict, revelar: bool = False) -> dict:
    dados = {
        "id": p.id,
        "chave": p.chave,
        "categoria": p.categoria,
        "descricao": p.descricao,
        "secreto": p.secreto,
        "tipo": p.tipo,
        "tem_valor": bool(p.valor),
        "valor": p.valor if (revelar or not p.secreto) else ("••••••••" if p.valor else ""),
    }
    if p.tipo == "caminho" and p.valor:
        dados["caminho"] = analisar_caminho(p.valor, mapa)
    return dados


@router.get("")
@limiter.limit(RATE_LIMITS["api_default"])
async def listar(request: Request, db: Session = Depends(get_db), user: User = Depends(exigir_admin)):
    mapa = _mapa(db)
    params = db.query(Parametro).order_by(Parametro.categoria, Parametro.chave).all()
    return {
        "categorias": CATEGORIAS,
        "parametros": [_serializar(p, mapa) for p in params],
    }


@router.get("/{chave}")
@limiter.limit(RATE_LIMITS["api_default"])
async def obter_um(
    request: Request,
    chave: str,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    p = db.query(Parametro).filter(Parametro.chave == chave).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Parâmetro {chave!r} não encontrado")
    return _serializar(p, _mapa(db))


@router.put("/{chave}")
async def atualizar(
    chave: str,
    payload: ParametroUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    p = db.query(Parametro).filter(Parametro.chave == chave).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Parâmetro {chave!r} não existe")
    p.valor = payload.valor.strip()
    db.commit()
    db.refresh(p)
    return _serializar(p, _mapa(db))


@router.post("")
async def criar(
    payload: ParametroCreate,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    chave = payload.chave.strip().lower().replace(" ", "_")
    if not chave:
        raise HTTPException(status_code=400, detail="Chave obrigatória")
    if payload.categoria not in CATEGORIAS:
        raise HTTPException(status_code=400, detail=f"Categoria deve ser uma de: {CATEGORIAS}")
    if db.query(Parametro).filter(Parametro.chave == chave).first():
        raise HTTPException(status_code=400, detail=f"Parâmetro {chave!r} já existe")

    p = Parametro(
        chave=chave,
        valor=payload.valor.strip(),
        categoria=payload.categoria,
        descricao=payload.descricao.strip(),
        secreto=payload.secreto or payload.tipo == "senha",
        tipo=payload.tipo,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serializar(p, _mapa(db))


@router.delete("/{chave}")
async def excluir(
    chave: str,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    p = db.query(Parametro).filter(Parametro.chave == chave).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parâmetro não encontrado")
    db.delete(p)
    db.commit()
    return {"excluido": chave}


@router.get("/deslocamento")
async def get_deslocamento(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Busca parâmetros de deslocamento (salário mínimo, custos, pedágios)"""
    import json
    p = db.query(Parametro).filter(Parametro.chave == "deslocamento_config").first()
    if not p:
        return {
            "salario_minimo": 1621,
            "alimentacao_diaria": 75,
            "custo_junior": 540,
            "custo_pleno": 810,
            "custo_senior": 1621,
            "usar_salario_minimo": True,
            "pedagios": {}
        }
    try:
        return json.loads(p.valor)
    except json.JSONDecodeError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao parsear JSON de deslocamento_config: {str(e)}", exc_info=True)
        return {}


class DeslocamentoConfig(BaseModel):
    salario_minimo: float = 1621
    alimentacao_diaria: float = 75
    custo_junior: float = 540
    custo_pleno: float = 810
    custo_senior: float = 1621
    usar_salario_minimo: bool = True
    pedagios: dict = {}


@router.post("/deslocamento")
async def save_deslocamento(
    config: DeslocamentoConfig,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """Salva parâmetros de deslocamento"""
    import json
    p = db.query(Parametro).filter(Parametro.chave == "deslocamento_config").first()
    if not p:
        p = Parametro(
            chave="deslocamento_config",
            categoria="valores",
            tipo="json",
            descricao="Configuração de deslocamento: SM, custos de perito, pedágios"
        )
        db.add(p)
    p.valor = json.dumps(config.dict())
    db.commit()
    return {"salvo": True}


@router.get("/agente")
async def parametros_do_agente(
    db: Session = Depends(get_db),
    _=Depends(verificar_agente),
):
    """Credenciais e caminhos com valores REAIS, para o agente Mac.
    Assim o Bruno troca uma senha na UI e o agente usa na hora, sem redeploy."""
    mapa = _mapa(db)
    params = (
        db.query(Parametro)
        .filter(Parametro.categoria.in_(["credenciais", "urls", "caminhos"]))
        .all()
    )
    resultado = {}
    for p in params:
        valor = p.valor
        if p.tipo == "caminho" and valor:
            valor = analisar_caminho(valor, mapa)["resolvido"]
        resultado[p.chave] = valor
    return resultado
