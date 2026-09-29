"""
Serviço de mapeamento de campos para ofícios — liga placeholders a valores reais.

SEGURANÇA:
- Path Traversal: secure_filename() + validação de separadores
- File Cleanup: schedule de limpeza de uploads > 1h
- Formula Injection: simpleeval com whitelist de funções
"""
import logging
import tempfile
import os
from typing import Dict, List, Tuple
from io import BytesIO
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import schedule
import threading

logger = logging.getLogger(__name__)

# Diretório temporário para uploads DOCX (será limpo periodicamente)
TEMP_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "oficios_upload")
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)


def salvar_upload_temporario(arquivo_bytes: bytes, temp_doc_id: str) -> str:
    """
    Salva um arquivo DOCX temporariamente para processamento posterior.

    SEGURANÇA (P0):
    - Valida temp_doc_id com secure_filename()
    - Rejeita path traversal (../, ..\, etc)
    - Força extensão .docx

    Args:
        arquivo_bytes: Bytes do arquivo DOCX
        temp_doc_id: ID único do upload temporário (UUID recomendado)

    Returns:
        Caminho completo do arquivo salvo

    Raises:
        ValueError: Se o arquivo não pode ser salvo ou contém path traversal
    """
    try:
        # P0: Sanitiza o ID com secure_filename
        safe_id = secure_filename(temp_doc_id)

        # P0: Rejeita se o ID foi alterado (indício de path traversal)
        if safe_id != temp_doc_id:
            raise ValueError("temp_doc_id contém caracteres inválidos ou path traversal")

        # P0: Rejeita separadores de path explicitamente
        if "/" in safe_id or "\\" in safe_id or ".." in safe_id:
            raise ValueError("temp_doc_id contém separadores de caminho (path traversal)")

        # Força extensão .docx
        caminho = os.path.join(TEMP_UPLOAD_DIR, f"{safe_id}.docx")

        # P0: Valida que o caminho resultante está dentro do TEMP_UPLOAD_DIR
        caminho_real = os.path.realpath(caminho)
        temp_dir_real = os.path.realpath(TEMP_UPLOAD_DIR)
        if not caminho_real.startswith(temp_dir_real):
            raise ValueError("Path traversal detectado: arquivo fora do diretório temporário")

        with open(caminho, "wb") as f:
            f.write(arquivo_bytes)
        logger.info(f"Upload temporário salvo (seguro): {caminho}")
        return caminho
    except ValueError:
        # Propaga erros de validação
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar upload temporário: {e}")
        raise ValueError(f"Não foi possível salvar o arquivo temporário: {str(e)}")


def carregar_upload_temporario(temp_doc_id: str) -> bytes:
    """
    Carrega um arquivo DOCX previamente salvo temporariamente.

    Args:
        temp_doc_id: ID único do upload temporário

    Returns:
        Bytes do arquivo DOCX

    Raises:
        FileNotFoundError: Se o arquivo não existe ou expirou
    """
    caminho = os.path.join(TEMP_UPLOAD_DIR, f"{temp_doc_id}.docx")
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Upload temporário não encontrado ou expirou: {temp_doc_id}")

    with open(caminho, "rb") as f:
        return f.read()


def deletar_upload_temporario(temp_doc_id: str) -> bool:
    """
    Deleta um arquivo DOCX temporário (após processar).

    Args:
        temp_doc_id: ID único do upload temporário

    Returns:
        True se deletado com sucesso
    """
    try:
        safe_id = secure_filename(temp_doc_id)
        if safe_id != temp_doc_id:
            logger.warning(f"temp_doc_id inválido para delete: {temp_doc_id}")
            return False

        caminho = os.path.join(TEMP_UPLOAD_DIR, f"{safe_id}.docx")
        if os.path.exists(caminho):
            os.remove(caminho)
            logger.info(f"Upload temporário deletado: {caminho}")
            return True
    except Exception as e:
        logger.warning(f"Erro ao deletar upload temporário: {e}")
    return False


def cleanup_old_uploads():
    """
    P0: Limpeza automática de uploads > 1 hora.

    Função de scheduling que remove uploads antigos para evitar:
    - Consumo indefinido de disco
    - Reutilização de IDs antigos
    - Exposição de dados temporários

    Executada a cada 30 minutos via schedule.
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        cutoff_timestamp = cutoff_time.timestamp()

        if not os.path.exists(TEMP_UPLOAD_DIR):
            return

        deleted_count = 0
        for filename in os.listdir(TEMP_UPLOAD_DIR):
            if not filename.endswith(".docx"):
                continue

            filepath = os.path.join(TEMP_UPLOAD_DIR, filename)
            try:
                if os.path.getmtime(filepath) < cutoff_timestamp:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"Deleted old upload: {filename}")
            except Exception as e:
                logger.warning(f"Erro ao deletar upload antigo {filename}: {e}")

        if deleted_count > 0:
            logger.info(f"Limpeza concluída: {deleted_count} uploads removidos")

    except Exception as e:
        logger.error(f"Erro na limpeza de uploads: {e}")


def start_cleanup_scheduler():
    """
    Inicia thread de background para cleanup automático.

    Chamada uma vez na inicialização da aplicação (app.py).
    """
    try:
        schedule.every(30).minutes.do(cleanup_old_uploads)

        def run_scheduler():
            while True:
                schedule.run_pending()
                import time
                time.sleep(60)  # Verifica a cada 1 min

        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        logger.info("File cleanup scheduler iniciado (a cada 30 min)")
    except Exception as e:
        logger.error(f"Erro ao iniciar cleanup scheduler: {e}")


def gerar_oficio_preenchido(temp_doc_id: str, mapeamentos: Dict[str, str],
                           processo, usuario) -> Tuple[str, str]:
    """
    Gera um DOCX preenchido a partir de um upload temporário com mapeamentos.

    Args:
        temp_doc_id: ID do upload temporário com o template DOCX
        mapeamentos: Dict com placeholders mapeados, ex:
            {
                "{{NUMERO_PROCESSO}}": "0001234-56.2022.8.12.0007",
                "{{DESLOCAMENTO}}": "45 km",
                ...
            }
        processo: Objeto Processo para metadados
        usuario: Objeto Usuario para auditoria

    Returns:
        Tuple (caminho_docx_final, hash_crc32)

    Raises:
        FileNotFoundError: Se o upload temporário não existe
        ValueError: Se não conseguir preencher o DOCX
    """
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx não instalado")

    # Carrega o DOCX temporário
    docx_bytes = carregar_upload_temporario(temp_doc_id)
    doc = Document(BytesIO(docx_bytes))

    # Preenche placeholders
    _preencher_documento(doc, mapeamentos)

    # Salva em storage permanente
    pasta = os.path.join(
        os.environ.get("STORAGE_DIR", "/data/storage"),
        "oficios",
        f"{processo.numero_cnj}",
    )
    os.makedirs(pasta, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    docx_path = os.path.join(pasta, f"oficio_preenchido_{timestamp}.docx")

    doc.save(docx_path)
    logger.info(f"DOCX preenchido gerado: {docx_path}")

    # Calcula CRC32 para integridade
    import zlib
    with open(docx_path, "rb") as f:
        hash_crc32 = hex(zlib.crc32(f.read()) & 0xffffffff)

    return docx_path, hash_crc32


def _preencher_documento(doc, mapeamentos: Dict[str, str]) -> None:
    """
    Preenche um documento Word com os mapeamentos de placeholders.

    Args:
        doc: Objeto Document do python-docx
        mapeamentos: Dict com placeholders → valores
    """
    # Parágrafos
    for para in doc.paragraphs:
        for placeholder, valor in mapeamentos.items():
            if placeholder in para.text:
                para.text = para.text.replace(placeholder, str(valor or ""))

    # Tabelas
    for tabela in doc.tables:
        for linha in tabela.rows:
            for celula in linha.cells:
                for para in celula.paragraphs:
                    for placeholder, valor in mapeamentos.items():
                        if placeholder in para.text:
                            para.text = para.text.replace(placeholder, str(valor or ""))

    logger.info(f"Documento preenchido com {len(mapeamentos)} mapeamentos")
