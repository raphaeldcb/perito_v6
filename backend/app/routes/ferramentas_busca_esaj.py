"""Endpoint para buscar intimações ESAJ com browser-use automático."""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User
from app.services import get_db
from app.services.esaj_browser_automation import buscar_intimacoes_esaj
import os
from app.decorators.require_feature import require_feature_flag

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ferramentas", tags=["ferramentas"])


@router.post("/buscar-intimacoes-esaj")
async def buscar_intimacoes_esaj_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Busca intimações ESAJ com automação de browser (browser-use)."""
    cpf = os.environ.get("CPF_ESAJ", "")
    senha = os.environ.get("SENHA_ESAJ", "")

    if not cpf or not senha:
        return {
            "status": "erro",
            "mensagem": "CPF_ESAJ ou SENHA_ESAJ não configurados no .env",
        }

    try:
        resultado = buscar_intimacoes_esaj(cpf, senha)
        logger.info(f"✅ Busca ESAJ: {resultado['status']}")
        return resultado
    except Exception as e:
        logger.error(f"❌ Erro busca ESAJ: {e}")
        return {"status": "erro", "mensagem": str(e)}
