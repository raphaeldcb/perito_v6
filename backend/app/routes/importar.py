"""Importação de dados de outros sistemas: CSV e Projuris ADV.

- CSV: upload direto (admin), separador ';' ou ',' detectado automaticamente,
  encoding UTF-8 ou Latin-1. Colunas na rota GET /csv/modelo.
- Projuris ADV: sincronização via API REST (precisa de PROJURIS_BASE_URL e
  PROJURIS_TOKEN no ambiente). Sem credenciais, o endpoint informa o que falta
  em vez de fingir sucesso.
"""
import csv
import io
import os

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User
from app.services import get_db
from app.services.importer import upsert_processo, CAMPOS_PROCESSO

router = APIRouter(prefix="/api/v1/importar", tags=["importar"])


def exigir_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem importar dados")
    return user


@router.get("/csv/modelo")
async def modelo_csv(user: User = Depends(exigir_admin)):
    return {
        "colunas_aceitas": CAMPOS_PROCESSO + ["data_nomeacao"],
        "obrigatorias": ["numero_cnj (ou external_id de registro já importado)"],
        "separador": "; ou , (detectado automaticamente)",
        "exemplo": "numero_cnj;titulo;autor;reu;vara;tribunal;especialidade;external_id",
    }


@router.post("/csv")
async def importar_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    conteudo = await file.read()
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")

    try:
        dialect = csv.Sniffer().sniff(texto[:2048], delimiters=";,")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(texto), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vazio ou sem cabeçalho")

    criados, atualizados = 0, 0
    erros = []
    for i, linha in enumerate(reader, start=2):
        dados = {(k or "").strip().lower(): v for k, v in linha.items()}
        try:
            _, criado = upsert_processo(db, dados, source_system="csv")
            criados += criado
            atualizados += not criado
        except ValueError as e:
            erros.append({"linha": i, "erro": str(e)})

    if erros and not (criados or atualizados):
        db.rollback()
        raise HTTPException(status_code=400, detail={"mensagem": "Nenhuma linha válida", "erros": erros[:20]})

    db.commit()
    return {"criados": criados, "atualizados": atualizados, "erros": erros[:20], "total_erros": len(erros)}


# --- Projuris ADV ---------------------------------------------------------
# Documentação da API: https://apidoc.projurisadv.com.br (conta ADV do usuário)
# Mapeamento de campos feito em _mapear_projuris; ajustar conforme o payload
# real da conta quando as credenciais forem configuradas.

def _mapear_projuris(item: dict) -> dict:
    return {
        "external_id": str(item.get("id") or item.get("processoId") or ""),
        "numero_cnj": item.get("numeroCnj") or item.get("numero") or "",
        "titulo": item.get("titulo") or item.get("pasta"),
        "autor": item.get("autor") or (item.get("parteAtiva") or {}).get("nome") if isinstance(item.get("parteAtiva"), dict) else item.get("parteAtiva"),
        "reu": item.get("reu") or (item.get("partePassiva") or {}).get("nome") if isinstance(item.get("partePassiva"), dict) else item.get("partePassiva"),
        "vara": item.get("vara"),
        "tribunal": item.get("tribunal") or item.get("orgao"),
        "juiz": item.get("juiz"),
        "especialidade": item.get("area") or item.get("especialidade"),
        "status": item.get("status") or "ativo",
    }


@router.get("/projuris/status")
async def status_projuris(user: User = Depends(exigir_admin)):
    base_url = os.environ.get("PROJURIS_BASE_URL", "")
    token = os.environ.get("PROJURIS_TOKEN", "")
    return {
        "configurado": bool(base_url and token),
        "base_url": base_url or "(defina PROJURIS_BASE_URL no .env)",
        "token": "configurado" if token else "(defina PROJURIS_TOKEN no .env)",
    }


@router.post("/projuris/sincronizar")
async def sincronizar_projuris(
    pagina_inicial: int = 1,
    max_paginas: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    base_url = os.environ.get("PROJURIS_BASE_URL", "").rstrip("/")
    token = os.environ.get("PROJURIS_TOKEN", "")
    if not base_url or not token:
        raise HTTPException(
            status_code=503,
            detail="Integração Projuris não configurada: defina PROJURIS_BASE_URL e "
                   "PROJURIS_TOKEN no .env do backend e reinicie o serviço.",
        )

    criados, atualizados = 0, 0
    erros = []
    async with httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {token}"}) as client:
        for pagina in range(pagina_inicial, pagina_inicial + max_paginas):
            resp = await client.get(f"{base_url}/processos", params={"pagina": pagina})
            if resp.status_code == 401:
                raise HTTPException(status_code=502, detail="Projuris recusou o token (401)")
            resp.raise_for_status()
            corpo = resp.json()
            itens = corpo if isinstance(corpo, list) else corpo.get("itens") or corpo.get("content") or []
            if not itens:
                break
            for item in itens:
                try:
                    _, criado = upsert_processo(db, _mapear_projuris(item), source_system="projuris")
                    criados += criado
                    atualizados += not criado
                except ValueError as e:
                    erros.append(str(e))

    db.commit()
    return {"criados": criados, "atualizados": atualizados, "erros": erros[:20], "total_erros": len(erros)}
