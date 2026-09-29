"""Modelos de documentos — listar (usuário) e sincronizar (agente Mac)."""
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

GERADOS_DIR = "/app/gerados"

from app.middleware import get_current_user
from app.models import User, Modelo, Processo, Job
from app.routes.jobs import verificar_agente
from app.services import get_db
from app.services import oficio

router = APIRouter(prefix="/api/v1/modelos", tags=["modelos"])


def _categoria(nome: str, pasta: str) -> str:
    nl = nome.lower()
    n = f"{pasta} {nome}".lower()
    if "laudo" in n:
        return "laudo"
    if "proposta" in n:
        return "proposta"
    if "contrato" in n:
        return "contrato"
    if "tabela" in n or "calculo" in nl or nl.endswith(".xlsx"):
        return "tabela"
    # ofício: começa com "of" (of, of-, ofício, ofcredenciamento, oficio17...)
    if nl.startswith("of") or "oficio" in n or "ofício" in n or "of -" in nl:
        return "oficio"
    return "outro"


@router.get("")
async def listar_modelos(
    categoria: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Modelo).filter(Modelo.ativo == True)
    if categoria:
        q = q.filter(Modelo.categoria == categoria)
    modelos = q.order_by(Modelo.pasta, Modelo.nome).all()
    return [
        {"id": m.id, "nome": m.nome, "pasta": m.pasta, "tipo": m.tipo,
         "categoria": m.categoria, "caminho": m.caminho_relativo}
        for m in modelos
    ]


class SyncModelos(BaseModel):
    arquivos: list[dict]   # [{nome, caminho_relativo, pasta, tipo}]


@router.post("/sync")
async def sync_modelos(
    payload: SyncModelos,
    db: Session = Depends(get_db),
    _=Depends(verificar_agente),
):
    """O agente Mac envia a lista de arquivos da pasta MODELOS do OneDrive."""
    novos, atualizados = 0, 0
    for a in payload.arquivos:
        caminho = a.get("caminho_relativo")
        if not caminho:
            continue
        existente = db.query(Modelo).filter(Modelo.caminho_relativo == caminho).first()
        if existente:
            # atualiza campos se o modelo ainda não os tinha (ex: .doc recém-convertido)
            if not existente.campos and a.get("campos"):
                existente.campos = a["campos"]
                atualizados += 1
            continue
        nome = a.get("nome", os.path.basename(caminho))
        pasta = a.get("pasta", "")
        db.add(Modelo(
            nome=nome, caminho_relativo=caminho, pasta=pasta,
            tipo=a.get("tipo", ""), categoria=_categoria(nome, pasta),
            campos=a.get("campos") or None,
        ))
        novos += 1
    db.commit()
    return {"recebidos": len(payload.arquivos), "novos": novos, "atualizados": atualizados}


class SalvarCampos(BaseModel):
    campos: list[str]


@router.post("/{modelo_id}/campos")
async def salvar_campos(
    modelo_id: int, payload: SalvarCampos,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """Salva campos (ex: sugeridos pelo Qwen) no modelo, para reuso sem re-analisar."""
    m = db.query(Modelo).filter(Modelo.id == modelo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    atuais = list(m.campos or [])
    for c in payload.campos:
        if c and c not in atuais:
            atuais.append(c)
    m.campos = atuais
    db.commit()
    return {"campos": atuais}


@router.post("/upload-gerado")
async def upload_gerado(
    job_id: int, arquivo: UploadFile = File(...),
    db: Session = Depends(get_db), _=Depends(verificar_agente),
):
    """O agente Mac envia o .docx gerado para o usuário poder baixar na tela."""
    os.makedirs(GERADOS_DIR, exist_ok=True)
    destino = os.path.join(GERADOS_DIR, f"{job_id}.docx")
    with open(destino, "wb") as f:
        f.write(await arquivo.read())
    return {"ok": True}


@router.get("/gerado/{job_id}")
async def baixar_gerado(job_id: int, token: str = "", db: Session = Depends(get_db)):
    """Baixa o documento gerado. Aceita token na query (link direto de download)."""
    from app.services import decode_token
    if not token or not decode_token(token):
        raise HTTPException(status_code=401, detail="Token inválido ou ausente")
    caminho = os.path.join(GERADOS_DIR, f"{job_id}.docx")
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Documento ainda não disponível")
    return FileResponse(caminho, filename=f"documento_{job_id}.docx",
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/{modelo_id}")
async def detalhe_modelo(modelo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.query(Modelo).filter(Modelo.id == modelo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    return {"id": m.id, "nome": m.nome, "caminho": m.caminho_relativo,
            "tipo": m.tipo, "categoria": m.categoria, "campos": m.campos or []}


CAMPOS_PADRAO = [
    "Nº", "VARA", "COMARCA", "ESTADO", "CIDADE", "AUTOR", "REU", "JUIZ",
    "ESPECIALIDADE", "HONORARIOS", "VALOR", "RESPONSAVEL", "DATA",
]


@router.post("/{modelo_id}/sugerir-campos")
async def sugerir_campos(
    modelo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Qwen analisa o conteúdo do modelo e SUGERE campos úteis além dos padrão.
    Ex: ofício de vistoria com deslocamento → sugere «VALOR_RESSARCIMENTO»,
    «MOTIVO_NAO_VISTORIA». Roda no agente Mac (Qwen local)."""
    m = db.query(Modelo).filter(Modelo.id == modelo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    job = Job(tipo="sugerir_campos", status="na_fila", payload={
        "modelo_caminho": m.caminho_relativo, "modelo_nome": m.nome,
        "campos_atuais": m.campos or [], "campos_padrao": CAMPOS_PADRAO,
    })
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.id, "mensagem": "Qwen analisando o documento para sugerir campos."}


class GerarDoc(BaseModel):
    processo_id: int | None = None
    valores_extras: dict = {}    # campos preenchidos manualmente pelo usuário


@router.post("/{modelo_id}/gerar")
async def gerar_documento(
    modelo_id: int,
    payload: GerarDoc,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Gera um documento a partir do modelo, preenchendo os «campos» com os
    dados do processo + valores manuais. Roda no agente Mac (preserva formatação)."""
    m = db.query(Modelo).filter(Modelo.id == modelo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    if m.tipo not in ("docx", "doc"):
        raise HTTPException(status_code=400, detail="Só modelos Word (.docx/.doc) podem ser gerados")

    valores = dict(payload.valores_extras or {})
    if payload.processo_id:
        proc = db.query(Processo).filter(Processo.id == payload.processo_id).first()
        if proc:
            base = oficio.valores_do_processo(proc, payload.valores_extras)
            valores = base

    preenchidos, faltando = oficio.resolver_campos(m.campos or [], valores)
    if faltando:
        # devolve o que falta para o usuário preencher (manual) antes de gerar
        return {"pronto": False, "faltando": faltando, "preenchidos": list(preenchidos.keys()),
                "mensagem": "Preencha os campos que faltam e gere novamente."}

    job = Job(tipo="gerar_documento", status="na_fila", payload={
        "modelo_caminho": m.caminho_relativo, "modelo_nome": m.nome,
        "valores": preenchidos, "processo_id": payload.processo_id,
    })
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"pronto": True, "job_id": job.id,
            "mensagem": "Documento sendo gerado no Mac. Acompanhe em /api/v1/jobs/{id}."}
