"""Routes for coletador CNAB payment module."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.middleware import get_current_user, exigir_admin
from app.models import User
from app.services import get_db
from .schemas import GerarCNABRequest, ValidarCNABResponse, GerarCNABResponse
from .service import ColetadorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/coletador", tags=["coletador_cnab"])


@router.post("/gerar-cnab", response_model=GerarCNABResponse)
async def gerar_cnab(
    request: GerarCNABRequest,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """
    Gera arquivo CNAB240 para pagamento de coletadores.

    Retorna arquivo .rem pronto para submissão ao Banco Inter.
    Apenas admin pode gerar.
    """
    try:
        result = ColetadorService.gerar_cnab(request)

        logger.info(
            f"CNAB gerado por {user.email}: {result['beneficiarios']} beneficiários, "
            f"R$ {result['valor_total']:.2f}, arquivo={result['arquivo']}"
        )

        return result

    except ValueError as e:
        logger.error(f"Erro de validação ao gerar CNAB: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao gerar CNAB: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar CNAB: {str(e)}")


@router.post("/validar-cnab", response_model=ValidarCNABResponse)
async def validar_cnab(
    request: GerarCNABRequest,
    db: Session = Depends(get_db),
    user: User = Depends(exigir_admin),
):
    """Valida dados de beneficiários sem gerar arquivo."""
    try:
        result = ColetadorService.validar_beneficiarios(request.beneficiarios)
        return result

    except ValueError as e:
        logger.error(f"Erro ao validar CNAB: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao validar CNAB: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao validar CNAB: {str(e)}")
