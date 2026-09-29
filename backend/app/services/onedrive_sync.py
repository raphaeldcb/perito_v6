"""Serviço de sincronização de templates de ofício do OneDrive.

Responsável por:
1. Conectar ao Microsoft Graph API
2. Sincronizar pasta MODELOS do OneDrive
3. Extrair placeholders de arquivos .docx
4. Criar/atualizar OfficioTemplateVersion no BD
5. Detectar mudanças por hash SHA-256
"""

import hashlib
import logging
import os
import re
import time
from datetime import datetime
from io import BytesIO

import requests
from sqlalchemy.orm import Session
from docx import Document

from app.models.kanban import OfficioTemplateVersion
from app.services.database import SessionLocal

logger = logging.getLogger(__name__)

# Configurações Microsoft Graph
TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
ONEDRIVE_FOLDER_PATH = os.getenv(
    "ONEDRIVE_FOLDER_PATH",
    "/drive/root:/IPCMS - ARQUIVOS/MODELOS"
)

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

# Cache de token
_token_cache = {"token": None, "expira": 0}


def configurado() -> bool:
    """Verifica se as credenciais do Azure estão configuradas."""
    return bool(TENANT_ID and CLIENT_ID and CLIENT_SECRET)


def _obter_token() -> str:
    """Obtém token de acesso ao Microsoft Graph (com cache)."""
    # Verifica cache
    if _token_cache["token"] and time.time() < _token_cache["expira"] - 60:
        return _token_cache["token"]

    logger.debug("Requisitando novo token ao Azure...")
    try:
        resp = requests.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Falha ao obter token Azure: {e}")

    corpo = resp.json()
    if "access_token" not in corpo:
        errmsg = corpo.get("error_description", str(corpo)[:300])
        raise RuntimeError(f"Falha no token Graph: {errmsg}")

    _token_cache["token"] = corpo["access_token"]
    _token_cache["expira"] = time.time() + int(corpo.get("expires_in", 3600))
    logger.debug("Token obtido com sucesso")
    return _token_cache["token"]


def _fazer_request_graph(metodo: str, endpoint: str, **kwargs) -> dict:
    """Faz uma requisição ao Microsoft Graph com token."""
    if not configurado():
        raise RuntimeError("Credenciais do Azure não configuradas")

    token = _obter_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    url = f"{GRAPH_API_URL}{endpoint}"
    logger.debug(f"[{metodo}] {endpoint}")

    try:
        if metodo.upper() == "GET":
            resp = requests.get(url, headers=headers, timeout=30, **kwargs)
        elif metodo.upper() == "POST":
            resp = requests.post(url, headers=headers, timeout=30, **kwargs)
        else:
            raise ValueError(f"Método HTTP não suportado: {metodo}")

        resp.raise_for_status()
        return resp.json() if resp.text else {}
    except requests.RequestException as e:
        logger.error(f"Erro na requisição Graph: {e}")
        raise


def _obter_id_pasta_modelos() -> str:
    """Obtém o ID da pasta MODELOS no OneDrive."""
    logger.info(f"Buscando pasta: {ONEDRIVE_FOLDER_PATH}")

    # Endpoint para acessar por caminho
    # Usar /me/drive/root:/caminho/aqui: para buscar por caminho
    endpoint = f"/me/drive/root:/{ONEDRIVE_FOLDER_PATH}:"
    try:
        resultado = _fazer_request_graph("GET", endpoint)
        pasta_id = resultado.get("id")
        if not pasta_id:
            logger.error(f"Pasta não encontrada: {ONEDRIVE_FOLDER_PATH}")
            raise RuntimeError(f"Pasta OneDrive não encontrada: {ONEDRIVE_FOLDER_PATH}")
        logger.info(f"Pasta encontrada com ID: {pasta_id}")
        return pasta_id
    except Exception as e:
        logger.error(f"Erro ao obter ID da pasta: {e}")
        raise


def _listar_arquivos_docx(pasta_id: str) -> list:
    """Lista todos os arquivos .docx na pasta."""
    logger.info("Listando arquivos .docx...")
    endpoint = f"/me/drive/items/{pasta_id}/children"

    try:
        resultado = _fazer_request_graph("GET", endpoint)
        itens = resultado.get("value", [])
        docx_files = [i for i in itens if i.get("name", "").endswith(".docx")]
        logger.info(f"Encontrados {len(docx_files)} arquivos .docx")
        return docx_files
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        raise


def _baixar_arquivo(item: dict) -> bytes:
    """Baixa o conteúdo de um arquivo do OneDrive."""
    nome = item.get("name", "desconhecido")
    url_download = item.get("@microsoft.graph.downloadUrl")

    if not url_download:
        raise RuntimeError(f"URL de download não disponível para: {nome}")

    logger.debug(f"Baixando: {nome}")
    try:
        resp = requests.get(url_download, timeout=60)
        resp.raise_for_status()
        logger.debug(f"Arquivo baixado: {nome} ({len(resp.content)} bytes)")
        return resp.content
    except requests.RequestException as e:
        logger.error(f"Erro ao baixar {nome}: {e}")
        raise


def _extrair_placeholders(docx_bytes: bytes) -> list:
    """Extrai placeholders ({{CAMPO}}) de um arquivo DOCX."""
    logger.debug("Extraindo placeholders do DOCX...")
    try:
        doc = Document(BytesIO(docx_bytes))
        placeholders = set()

        # Buscar em parágrafos
        for paragrafo in doc.paragraphs:
            matches = re.findall(r"\{\{[A-Z_]+\}\}", paragrafo.text)
            placeholders.update(matches)

        # Buscar em tabelas
        for tabela in doc.tables:
            for linha in tabela.rows:
                for celula in linha.cells:
                    matches = re.findall(r"\{\{[A-Z_]+\}\}", celula.text)
                    placeholders.update(matches)

        lista_placeholders = sorted(list(placeholders))
        logger.debug(f"Placeholders encontrados: {lista_placeholders}")
        return lista_placeholders
    except Exception as e:
        logger.error(f"Erro ao extrair placeholders: {e}")
        raise


def _parse_nome_arquivo(filename: str) -> tuple:
    """
    Parse do nome do arquivo seguindo a convenção:
    oficio_<tipo>_<versao>.docx
    Ex: "oficio_proposta_v2.1.docx" → ("proposta", "v2.1")
    """
    pattern = r"^oficio_(\w+)_(v\d+\.\d+)\.docx$"
    match = re.match(pattern, filename)
    if match:
        tipo = match.group(1)
        versao = match.group(2)
        return tipo, versao
    return None, None


def _processar_arquivo(
    db: Session, item: dict, docx_bytes: bytes
) -> dict:
    """Processa um arquivo .docx e cria/atualiza OfficioTemplateVersion."""
    filename = item.get("name", "")
    item_id = item.get("id")

    logger.info(f"Processando arquivo: {filename} (ID: {item_id})")

    # Parse do nome
    tipo, versao = _parse_nome_arquivo(filename)
    if not tipo or not versao:
        logger.warning(
            f"Arquivo não segue convenção (esperado: oficio_<tipo>_v<num>.<num>.docx): {filename}"
        )
        return {"status": "skipped", "reason": "Nome inválido"}

    # Calcular hash
    hash_novo = hashlib.sha256(docx_bytes).hexdigest()

    # Extrair placeholders
    try:
        placeholders = _extrair_placeholders(docx_bytes)
    except Exception as e:
        logger.error(f"Erro ao extrair placeholders de {filename}: {e}")
        return {"status": "erro", "reason": str(e)}

    # Buscar template existente
    versao_numero = int(versao.split(".")[0][1:])  # v2.1 → 2

    template = db.query(OfficioTemplateVersion).filter(
        OfficioTemplateVersion.tipo == tipo,
        OfficioTemplateVersion.versao_numero == versao_numero,
    ).first()

    # Comparar hash
    if template and template.hash_docx == hash_novo:
        logger.info(
            f"Arquivo não mudou (hash igual): {filename} — pulando"
        )
        return {"status": "skipped", "reason": "Hash igual"}

    # Criar ou atualizar
    if template:
        template.conteudo_docx = docx_bytes
        placeholders_dict = {p: "" for p in placeholders}
        template.placeholders = placeholders_dict
        template.hash_docx = hash_novo
        template.source = "onedrive"
        template.onedrive_item_id = item_id
        template.last_sync_at = datetime.utcnow()
        db.commit()
        logger.info(f"Template atualizado: {tipo} {versao}")
        return {
            "status": "updated",
            "tipo": tipo,
            "versao": versao,
            "id": template.id,
        }
    else:
        # Criar novo
        placeholders_dict = {p: "" for p in placeholders}
        novo_template = OfficioTemplateVersion(
            nome=f"Modelo {tipo} {versao}",
            tipo=tipo,
            versao_numero=versao_numero,
            versao_string=versao,
            conteudo_docx=docx_bytes,
            placeholders=placeholders_dict,
            created_by_id=None,  # OneDrive sync (sem usuário)
            is_ativa=True,
            hash_docx=hash_novo,
            source="onedrive",
            onedrive_item_id=item_id,
            last_sync_at=datetime.utcnow(),
        )
        db.add(novo_template)
        db.commit()
        logger.info(f"Template criado: {tipo} {versao}")
        return {
            "status": "created",
            "tipo": tipo,
            "versao": versao,
            "id": novo_template.id,
        }


def sincronizar_modelos() -> dict:
    """
    Job principal: sincroniza pasta MODELOS do OneDrive → BD.
    Retorna estatísticas de sincronização.
    """
    if not configurado():
        logger.warning("OneDrive sync DESABILITADO: credenciais Azure não configuradas")
        return {
            "status": "disabled",
            "message": "Credenciais Azure não configuradas",
        }

    logger.info("Iniciando sincronização de templates OneDrive...")
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "criados": 0,
        "atualizados": 0,
        "pulados": 0,
        "erros": 0,
        "erros_detalhes": [],
        "templates_sincronizadas": [],
    }

    db = SessionLocal()
    try:
        # 1. Obter pasta MODELOS
        pasta_id = _obter_id_pasta_modelos()

        # 2. Listar arquivos .docx
        arquivos = _listar_arquivos_docx(pasta_id)

        # 3. Processar cada arquivo
        for item in arquivos:
            try:
                docx_bytes = _baixar_arquivo(item)
                resultado = _processar_arquivo(db, item, docx_bytes)

                if resultado["status"] == "created":
                    stats["criados"] += 1
                    stats["templates_sincronizadas"].append(resultado)
                elif resultado["status"] == "updated":
                    stats["atualizados"] += 1
                    stats["templates_sincronizadas"].append(resultado)
                elif resultado["status"] == "skipped":
                    stats["pulados"] += 1
                else:
                    stats["erros"] += 1
                    stats["erros_detalhes"].append(resultado)

            except Exception as e:
                logger.error(f"Erro ao processar arquivo: {e}")
                stats["erros"] += 1
                stats["erros_detalhes"].append({
                    "arquivo": item.get("name"),
                    "erro": str(e),
                })

        logger.info(
            f"Sincronização concluída: "
            f"{stats['criados']} criados, "
            f"{stats['atualizados']} atualizados, "
            f"{stats['pulados']} pulados, "
            f"{stats['erros']} erros"
        )
        stats["status"] = "success"
        return stats

    except Exception as e:
        logger.error(f"Falha geral na sincronização: {e}")
        stats["status"] = "error"
        stats["error"] = str(e)
        return stats

    finally:
        db.close()


def obter_status_ultimo_sync() -> dict:
    """Obtém informações do último sync bem-sucedido."""
    db = SessionLocal()
    try:
        # Buscar último template sincronizado do OneDrive
        templates_onedrive = db.query(OfficioTemplateVersion).filter(
            OfficioTemplateVersion.source == "onedrive",
            OfficioTemplateVersion.last_sync_at.isnot(None),
        ).order_by(OfficioTemplateVersion.last_sync_at.desc()).first()

        if not templates_onedrive:
            return {
                "ultima_sync": None,
                "templates_onedrive": 0,
                "templates_total": 0,
            }

        total = db.query(OfficioTemplateVersion).count()
        onedrive_count = db.query(OfficioTemplateVersion).filter(
            OfficioTemplateVersion.source == "onedrive"
        ).count()

        return {
            "ultima_sync": templates_onedrive.last_sync_at.isoformat(),
            "templates_onedrive": onedrive_count,
            "templates_total": total,
        }
    finally:
        db.close()
