import logging
import os
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Laudo, LaudoVersao

logger = logging.getLogger(__name__)

SAFESIGN_ENDPOINT = os.getenv("SAFESIGN_ENDPOINT", "https://safeweb.safesign.com.br")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT não instalado. Instale com: pip install PyJWT")


def gerar_url_assinatura(laudo_id: int, db: Session) -> dict:
    """Gera URL para assinar laudo via SafeSign modal."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise ValueError(f"Laudo {laudo_id} não encontrado")

    versao = db.query(LaudoVersao).filter(
        LaudoVersao.laudo_id == laudo_id
    ).order_by(LaudoVersao.numero_versao.desc()).first()

    if not versao:
        raise ValueError(f"Nenhuma versão do laudo {laudo_id}")

    pdf_temp_path = _gerar_pdf_temporario(laudo, versao)

    if JWT_AVAILABLE:
        payload = {
            "laudo_id": laudo_id,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    else:
        token = str(uuid.uuid4())
        logger.warning("JWT não disponível, usando token aleatório")

    url = f"/assinar-laudo?laudo_id={laudo_id}&token={token}"

    return {
        "url": url,
        "pdf_temp_path": pdf_temp_path,
        "token": token,
        "laudo_id": laudo_id
    }


def processar_callback_assinatura(laudo_id: int, pdf_assinado_bytes: bytes, db: Session) -> dict:
    """Processa PDF assinado retornado do SafeSign."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise ValueError(f"Laudo {laudo_id} não encontrado")

    arquivo_path = _salvar_pdf_assinado(laudo_id, pdf_assinado_bytes)

    laudo.arquivo_pdf_path = arquivo_path
    laudo.data_assinatura = datetime.utcnow()
    laudo.assinado_por = "SafeSign A3"
    laudo.status = "emitido"

    db.commit()
    db.refresh(laudo)

    logger.info(f"Laudo {laudo_id} assinado e salvo em: {arquivo_path}")

    return {
        "status": "emitido",
        "laudo_id": laudo_id,
        "arquivo_path": arquivo_path,
        "data_assinatura": laudo.data_assinatura.isoformat() if laudo.data_assinatura else None
    }


def _gerar_pdf_temporario(laudo: Laudo, versao: LaudoVersao) -> str:
    """Gera PDF temporário do rascunho Markdown (TODO: converter para PDF real)."""
    # TODO: Usar reportlab ou wkhtmltopdf para converter Markdown → PDF
    # Por enquanto, retorna path simulado
    temp_dir = "laudos_temporarios"
    os.makedirs(temp_dir, exist_ok=True)

    filename = f"{temp_dir}/laudo_{laudo.id}_temp_{uuid.uuid4().hex[:8]}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"LAUDO PERICIAL #{laudo.id}\n")
        f.write(f"Tipo: {laudo.tipo_laudo}\n")
        f.write(f"Processo: {laudo.processo_id}\n")
        f.write(f"Data: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("\n" + "="*80 + "\n\n")
        f.write(versao.conteudo_markdown or "[Sem conteúdo]")

    logger.info(f"PDF temporário criado: {filename}")
    return filename


def _salvar_pdf_assinado(laudo_id: int, pdf_bytes: bytes) -> str:
    """Salva PDF assinado permanentemente."""
    output_dir = "laudos_assinados"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{output_dir}/laudo_{laudo_id}_assinado_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    with open(filename, "wb") as f:
        f.write(pdf_bytes)

    logger.info(f"PDF assinado salvo: {filename}")
    return filename


def validar_token_assinatura(token: str) -> dict:
    """Valida token JWT do link de assinatura."""
    if not JWT_AVAILABLE:
        logger.warning("JWT não disponível para validação")
        return {"valid": False, "error": "JWT não configurado"}

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {
            "valid": True,
            "laudo_id": payload.get("laudo_id"),
            "payload": payload
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token expirado"}
    except jwt.InvalidTokenError as e:
        return {"valid": False, "error": f"Token inválido: {e}"}
