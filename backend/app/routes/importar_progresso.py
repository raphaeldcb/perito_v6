"""
Rotas para importação com rastreamento de progresso em tempo real.
WebSocket para atualizar barra de progresso no frontend.
"""
import asyncio
import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, WebSocket, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.middleware import get_current_user
from app.models import User
from app.services import get_db
from app.services.import_progress import (
    ImportProgress, DuplicataDetector, validar_mapeamento_csv
)
from app.services.importer import upsert_processo, CAMPOS_PROCESSO

router = APIRouter(prefix="/api/v1/importar", tags=["importar"])

# WebSocket para progresso em tempo real
active_connections: dict[str, list[WebSocket]] = {}

def exigir_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem importar dados")
    return user


@router.websocket("/progresso/ws")
async def websocket_progresso(websocket: WebSocket, session_id: str):
    """WebSocket para rastrear progresso de importação em tempo real."""
    await websocket.accept()

    if session_id not in active_connections:
        active_connections[session_id] = []

    active_connections[session_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Echo para manter vivo
            await websocket.send_text(json.dumps({"tipo": "pong"}))
    except Exception as e:
        active_connections[session_id].remove(websocket)
        if not active_connections[session_id]:
            del active_connections[session_id]


async def broadcast_progresso(session_id: str, progresso: dict):
    """Envia atualização de progresso para todas as conexões da sessão."""
    if session_id in active_connections:
        for websocket in active_connections[session_id]:
            try:
                await websocket.send_text(json.dumps({
                    "tipo": "progresso",
                    "dados": progresso
                }))
            except Exception:
                pass


@router.post("/validar-csv")
async def validar_csv_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
    session_id: str = Query(None)
):
    """
    Valida CSV antes de importar.
    Detecta duplicatas, mostra campos mapeados e permite seleção manual.
    """
    conteudo = await file.read()

    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")

    # Detectar separador
    try:
        dialect = csv.Sniffer().sniff(texto[:2048], delimiters=";,")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(texto), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vazio ou sem cabeçalho")

    csv_data = list(reader)

    # Validar com progresso
    async def progress_callback(progresso):
        if session_id:
            await broadcast_progresso(session_id, progresso)

    resultado = await validar_mapeamento_csv(csv_data, db, progress_callback)

    return {
        "arquivo": file.filename,
        "validacao": resultado,
        "colunas_disponiveis": CAMPOS_PROCESSO + ["data_nomeacao"],
        "proximo_passo": "Confirmar duplicatas ou importar linhas validadas"
    }


@router.post("/csv-com-progresso")
async def importar_csv_progresso(
    file: UploadFile = File(...),
    duplicatas_action: str = Query("revisar"),  # ignorar, revisar, cancelar
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
    session_id: str = Query(None)
):
    """
    Importa CSV com rastreamento de progresso.
    duplicatas_action:
    - "ignorar": importa tudo (sobrescreve)
    - "revisar": pula duplicatas (só importa linhas novas)
    - "cancelar": cancela se houver duplicatas
    """
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
    csv_data = list(reader)

    progress = ImportProgress(total=len(csv_data))

    async def progress_update():
        if session_id:
            await broadcast_progresso(session_id, progress.to_dict())

    criados = 0
    atualizados = 0
    duplicatas = 0
    erros = []

    for idx, linha in enumerate(csv_data):
        progress.current = idx + 1
        progress.etapa = f"Importando linha {idx + 1}/{len(csv_data)}"

        await progress_update()

        dados = {(k or "").strip().lower(): v for k, v in linha.items()}

        # Detectar duplicatas
        duplicatas_encontradas = DuplicataDetector.buscar_duplicatas_processo(
            db,
            numero_cnj=dados.get("numero_cnj"),
            titulo=dados.get("titulo")
        )

        if duplicatas_encontradas:
            duplicatas += 1

            if duplicatas_action == "cancelar":
                progress.status = "erro"
                progress.mensagem = f"Cancelado: encontradas {duplicatas} duplicatas"
                await progress_update()
                raise HTTPException(
                    status_code=409,
                    detail={
                        "mensagem": "Duplicatas encontradas",
                        "duplicatas": duplicatas_encontradas,
                        "acao_requerida": "Selecionar ação: ignorar ou revisar"
                    }
                )

            if duplicatas_action == "revisar":
                continue  # Pula duplicatas

        # Importar
        try:
            _, criado = upsert_processo(db, dados, source_system="csv-progresso")
            criados += criado
            atualizados += not criado
        except ValueError as e:
            erros.append({"linha": idx + 1, "erro": str(e)})

    db.commit()

    progress.status = "concluído"
    progress.mensagem = f"{criados} criados, {atualizados} atualizados, {duplicatas} duplicatas, {len(erros)} erros"
    await progress_update()

    return {
        "arquivo": file.filename,
        "criados": criados,
        "atualizados": atualizados,
        "duplicatas_encontradas": duplicatas,
        "erros": erros[:20],
        "total_erros": len(erros),
        "percentual_sucesso": round((criados + atualizados) / len(csv_data) * 100, 1)
    }


@router.get("/duplicatas/processos")
async def listar_duplicatas_processos(
    numero_cnj: Optional[str] = Query(None),
    titulo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin)
):
    """
    Busca registros duplicados potenciais no banco.
    Usado para mostrar ao usuário "isto já existe com outro nome".
    """
    if not numero_cnj and not titulo:
        raise HTTPException(
            status_code=400,
            detail="Forneça numero_cnj ou titulo para buscar duplicatas"
        )

    duplicatas = DuplicataDetector.buscar_duplicatas_processo(
        db,
        numero_cnj=numero_cnj,
        titulo=titulo
    )

    return {
        "entrada": {"numero_cnj": numero_cnj, "titulo": titulo},
        "duplicatas_encontradas": len(duplicatas),
        "registros": duplicatas,
        "recomendacao": "Se encontrar duplicatas, clique para usar o existente" if duplicatas else "Nenhuma duplicata — seguro para criar novo"
    }
