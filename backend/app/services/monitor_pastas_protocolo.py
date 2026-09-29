import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.models import Laudo, Job

logger = logging.getLogger(__name__)

# Caminhos Windows
PASTA_LAUDOS = os.getenv("PASTA_LAUDOS", r"D:\Laudos")
PASTA_OFICIOS = os.getenv("PASTA_OFICIOS", r"D:\Oficios")
PASTA_ENVIADOS = os.getenv("PASTA_ENVIADOS", r"D:\Enviados")

for pasta in [PASTA_LAUDOS, PASTA_OFICIOS, PASTA_ENVIADOS]:
    Path(pasta).mkdir(parents=True, exist_ok=True)
    logger.info(f"Pasta criada/verificada: {pasta}")


def monitorar_pastas(db: Session) -> dict:
    """Monitora D:\Laudos\ e D:\Oficios\ por PDFs novos."""
    resultado = {
        "laudos_encontrados": 0,
        "oficios_encontrados": 0,
        "jobs_enfileirados": 0,
        "erros": []
    }

    try:
        # Monitorar Laudos
        laudos_arquivos = list(Path(PASTA_LAUDOS).glob("*.pdf"))
        for arquivo in laudos_arquivos:
            try:
                resultado["laudos_encontrados"] += 1
                laudo_id = _extrair_laudo_id_e_enfileirar(arquivo, "laudo", db)
                if laudo_id:
                    resultado["jobs_enfileirados"] += 1
            except Exception as e:
                logger.error(f"Erro ao processar laudo {arquivo}: {e}")
                resultado["erros"].append(str(e))

        # Monitorar Ofícios
        oficios_arquivos = list(Path(PASTA_OFICIOS).glob("*.pdf"))
        for arquivo in oficios_arquivos:
            try:
                resultado["oficios_encontrados"] += 1
                laudo_id = _extrair_laudo_id_e_enfileirar(arquivo, "oficio", db)
                if laudo_id:
                    resultado["jobs_enfileirados"] += 1
            except Exception as e:
                logger.error(f"Erro ao processar ofício {arquivo}: {e}")
                resultado["erros"].append(str(e))

    except Exception as e:
        logger.error(f"Erro ao monitorar pastas: {e}")
        resultado["erros"].append(f"Monitor falhou: {e}")

    logger.info(f"Monitor pastas: {resultado}")
    return resultado


def _extrair_laudo_id_e_enfileirar(arquivo_path: Path, tipo: str, db: Session) -> int:
    """Extrai laudo_id do filename e enfileira job de protocolo."""
    filename = arquivo_path.name

    # Padrão: laudo_123.pdf ou oficio_456.pdf
    laudo_id = None
    try:
        partes = filename.replace(".pdf", "").split("_")
        if len(partes) >= 2:
            laudo_id = int(partes[-1])
    except (ValueError, IndexError):
        logger.warning(f"Não conseguiu extrair ID do filename: {filename}")
        return None

    if not laudo_id:
        return None

    # Verificar se laudo existe
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        logger.warning(f"Laudo {laudo_id} não encontrado no DB")
        return None

    # Enfileirar job de protocolo
    job = Job(
        tipo="protocolo",
        status="na_fila",
        payload={
            "laudo_id": laudo_id,
            "arquivo_path": str(arquivo_path),
            "tipo_documento": tipo,
            "numero_processo": laudo.processo_id
        }
    )
    db.add(job)
    db.commit()

    logger.info(f"Job protocolo enfileirado: laudo {laudo_id}, arquivo {filename}")
    return laudo_id


def mover_para_enviados(arquivo_path: str, numero_protocolo: str = None) -> str:
    """Move arquivo para D:\Enviados\ com timestamp."""
    try:
        arquivo = Path(arquivo_path)
        if not arquivo.exists():
            logger.warning(f"Arquivo não existe: {arquivo_path}")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        novo_nome = f"{arquivo.stem}_{timestamp}"
        if numero_protocolo:
            novo_nome = f"{numero_protocolo}_{timestamp}"
        novo_nome += ".pdf"

        novo_caminho = Path(PASTA_ENVIADOS) / novo_nome
        shutil.move(str(arquivo), str(novo_caminho))

        logger.info(f"Arquivo movido: {arquivo_path} → {novo_caminho}")
        return str(novo_caminho)

    except Exception as e:
        logger.error(f"Erro ao mover arquivo {arquivo_path}: {e}")
        return None
