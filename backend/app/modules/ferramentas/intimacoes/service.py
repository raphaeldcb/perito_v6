"""Serviços de negócio para intimações e modelos."""
import os
from app.utils import retry
import re
from app.utils import retry
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models import Intimacao, Processo, Job


CNJ_RE = re.compile(r"\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}")

# Modelos em memória (TODO: migrar pra DB)
MODELOS_DISPONIVEIS = [
    {
        "id": 1,
        "nome": "Modelo Padrão",
        "descricao": "Template padrão para ofícios",
        "categoria": "oficio",
        "ativo": True
    },
    {
        "id": 2,
        "nome": "Modelo Intimação",
        "descricao": "Template para intimações",
        "categoria": "intimacao",
        "ativo": True
    },
    {
        "id": 3,
        "nome": "Modelo Parecer",
        "descricao": "Template para pareceres",
        "categoria": "parecer",
        "ativo": True
    }
]


def _storage_path(subdir: str, filename: str) -> str:
    """Gera caminho de armazenamento seguro."""
    base = os.path.join(settings.storage_dir, subdir)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, filename)


def listar_modelos() -> List[dict]:
    """Lista todos os modelos disponíveis."""
    return MODELOS_DISPONIVEIS


def obter_modelo(modelo_id: int) -> Optional[dict]:
    """Obtém modelo específico por ID."""
    for modelo in MODELOS_DISPONIVEIS:
        if modelo["id"] == modelo_id:
            return modelo
    return None


def listar_modelos_por_categoria(categoria: str) -> List[dict]:
    """Lista modelos filtrados por categoria."""
    return [m for m in MODELOS_DISPONIVEIS if m["categoria"] == categoria]


def extrair_numero_processo(filename: str, numero_processo: Optional[str] = None) -> Optional[str]:
    """Extrai número de processo do nome do arquivo ou retorna o fornecido."""
    if numero_processo:
        return numero_processo

    match = CNJ_RE.search(filename or "")
    return match.group(0) if match else None


def criar_ou_obter_processo(numero_processo: str, db: Session) -> Processo:
    """Cria ou obtém processo existente."""
    processo = db.query(Processo).filter(Processo.numero_cnj == numero_processo).first()
    if not processo:
        processo = Processo(
            numero_cnj=numero_processo,
            titulo=f"Processo {numero_processo}",
            status="ativo",
            source_system="email",
        )
        db.add(processo)
        db.flush()
    return processo


def salvar_intimacao_arquivo(conteudo: bytes, numero_processo: str, filename: str) -> str:
    """Salva arquivo de intimação no disco."""
    nome_arquivo = f"{numero_processo}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf_path = _storage_path("intimacoes", nome_arquivo)
    with open(pdf_path, "wb") as f:
        f.write(conteudo)
    return pdf_path


def criar_intimacao_email(
    processo_id: int,
    pdf_path: str,
    filename: str,
    db: Session
) -> Intimacao:
    """Cria registro de intimação a partir de email."""
    intimacao = Intimacao(
        processo_id=processo_id,
        origem="email",
        tipo="intimacao",
        assunto=f"Email de intimação: {filename}",
        pdf_path=pdf_path,
        status="pendente",
        source_system="email",
    )
    db.add(intimacao)
    db.commit()
    db.refresh(intimacao)
    return intimacao


def validar_status_intimacao(novo_status: str) -> bool:
    """Valida se o status é permitido."""
    status_permitidos = ["pendente", "processada", "analisada", "erro"]
    return novo_status in status_permitidos


def enfileirar_download_esaj(
    numero_processo: str,
    tribunal: str,
    sistema: str,
    processo_id: int,
    db: Session
) -> Job:
    """Enfileira job de download ESAJ/eproc."""
    tipo_job = f"{sistema}_download"

    # Evita jobs duplicados
    job_aberto = (
        db.query(Job)
        .filter(
            Job.tipo == tipo_job,
            Job.status.in_(["na_fila", "processando"]),
            Job.payload["numero_cnj"].astext == numero_processo,
        )
        .first()
    )

    if job_aberto:
        return job_aberto

    job = Job(
        tipo=tipo_job,
        payload={"numero_cnj": numero_processo, "tribunal": tribunal, "processo_id": processo_id},
        status="na_fila",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
