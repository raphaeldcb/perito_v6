"""Router for padroes de cálculo (pattern calculation).

Padrões semânticos de cálculo — rota dedicada. Separada de app/routes/calculo.py
porque dispara um job assíncrono (BackgroundTasks) que lê o PDF oficial da decisão
e chama o Qwen, em vez de calcular na hora — mesmo prefixo (/api/v1/calculo), rota
nova (/aplicar-padrao) sem colidir com nada existente.
"""

import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import Job, PadraoCalculo, Processo, User
from app.services import get_db

from .schemas import AplicarPadraoInput, AplicarPadraoResponse
from .service import executar_padrao_em_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calculo", tags=["padroes"])


@router.post("/aplicar-padrao", response_model=AplicarPadraoResponse)
async def aplicar_padrao(
    payload: AplicarPadraoInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dispara o job de interpretação da decisão oficial: lê o PDF em
    processo.decisao_oficial_path, tokeniza padrao.regra_semantica e pede ao
    Qwen as datas de cada marco processual. Retorna imediatamente com o
    job_id — o resultado fica em GET /api/v1/jobs/{job_id} (ou consultando
    CalculoArvoreDecisao depois de concluído).

    Args:
        payload: Input with padrao_id and processo_id
        background_tasks: FastAPI background tasks
        db: Database session
        user: Current authenticated user

    Returns:
        AplicarPadraoResponse with job_id and status

    Raises:
        HTTPException 404: If padrao or processo not found
        HTTPException 404: If processo has no decisao_oficial_path
    """
    padrao = db.query(PadraoCalculo).filter(PadraoCalculo.id == payload.padrao_id).first()
    if not padrao:
        raise HTTPException(status_code=404, detail="Padrão não encontrado")

    processo = db.query(Processo).filter(Processo.id == payload.processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    if not processo.decisao_oficial_path:
        raise HTTPException(
            status_code=404,
            detail="Processo não tem PDF de decisão oficial cadastrado (processo.decisao_oficial_path)",
        )

    # Create background job record
    job = Job(
        tipo="interpretar_decisao_oficial",
        status="na_fila",
        payload={"padrao_id": payload.padrao_id, "processo_id": payload.processo_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue background task
    background_tasks.add_task(
        executar_padrao_em_background,
        job.id,
        payload.padrao_id,
        payload.processo_id,
    )

    return AplicarPadraoResponse(
        job_id=job.id,
        status="interpretando_decisao_oficial",
        mensagem="Buscando PDF da decisão nos autos...",
    )
