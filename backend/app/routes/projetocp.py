"""
ProjetoCP Routes — FastAPI endpoints para Processo, Comarca, Vara, Juiz.

PHASE 1: REST API endpoints (Comarcas, Varas, Juízes, Processos)
- POST /api/v1/processos (criar)
- GET /api/v1/processos (listar)
- GET /api/v1/processos/{id} (obter)
- PATCH /api/v1/processos/{id} (atualizar)
- Auth via middleware

PHASE 2: Laudos + Financeiro (30+ endpoints)
- Inclui subrouters para projetocp_laudos e projetocp_financeiro
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.services import get_db
from app.middleware import get_current_user
from app.services.projetocp import (
    ComarcaService, VaraService, JuizService, ProcessoService
)
from app.schemas.projetocp import (
    ComarcaCreate, ComarcaUpdate, ComarcaRead,
    VaraCreate, VaraUpdate, VaraRead,
    JuizCreate, JuizUpdate, JuizRead,
    ProcessoCreate, ProcessoUpdate, ProcessoRead, ProcessoListResponse,
    StatusProcesso
)
from app.decorators.require_feature import require_feature_flag

# Phase 2 imports
try:
    from app.routes.projetocp_laudos import router as laudos_phase2_router
    from app.routes.projetocp_financeiro import router as financeiro_phase2_router
    HAS_PHASE2 = True
except ImportError:
    HAS_PHASE2 = False

router = APIRouter()


# ============== COMARCA ENDPOINTS ==============

@router.post("/api/v1/comarcas", response_model=ComarcaRead, tags=["Comarcas"])
async def criar_comarca(
    comarca: ComarcaCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Criar nova Comarca."""
    try:
        db_comarca = ComarcaService.criar(db, comarca)
        return db_comarca
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/comarcas", response_model=dict, tags=["Comarcas"])
async def listar_comarcas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    uf: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Listar Comarcas com paginação."""
    total, items = ComarcaService.listar(db, skip=skip, limit=limit, uf=uf)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }


@router.get("/api/v1/comarcas/{comarca_id}", response_model=ComarcaRead, tags=["Comarcas"])
async def obter_comarca(
    comarca_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Obter Comarca por ID."""
    db_comarca = ComarcaService.obter_por_id(db, comarca_id)
    if not db_comarca:
        raise HTTPException(status_code=404, detail="Comarca não encontrada")
    return db_comarca


@router.patch("/api/v1/comarcas/{comarca_id}", response_model=ComarcaRead, tags=["Comarcas"])
async def atualizar_comarca(
    comarca_id: int,
    update: ComarcaUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Atualizar Comarca."""
    db_comarca = ComarcaService.atualizar(db, comarca_id, update)
    if not db_comarca:
        raise HTTPException(status_code=404, detail="Comarca não encontrada")
    return db_comarca


@router.delete("/api/v1/comarcas/{comarca_id}", tags=["Comarcas"])
async def deletar_comarca(
    comarca_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Deletar Comarca (soft delete)."""
    result = ComarcaService.deletar(db, comarca_id)
    if not result:
        raise HTTPException(status_code=404, detail="Comarca não encontrada")
    return {"ok": True, "message": "Comarca deletada (inativada)"}


# ============== VARA ENDPOINTS ==============

@router.post("/api/v1/varas", response_model=VaraRead, tags=["Varas"])
async def criar_vara(
    vara: VaraCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Criar nova Vara."""
    try:
        # Validar se Comarca existe
        comarca = ComarcaService.obter_por_id(db, vara.comarca_id)
        if not comarca:
            raise HTTPException(status_code=404, detail="Comarca não encontrada")

        db_vara = VaraService.criar(db, vara)
        return db_vara
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/varas", response_model=dict, tags=["Varas"])
async def listar_varas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    comarca_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Listar Varas com paginação."""
    total, items = VaraService.listar(db, comarca_id=comarca_id, skip=skip, limit=limit)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }


@router.get("/api/v1/varas/{vara_id}", response_model=VaraRead, tags=["Varas"])
async def obter_vara(
    vara_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Obter Vara por ID."""
    db_vara = VaraService.obter_por_id(db, vara_id)
    if not db_vara:
        raise HTTPException(status_code=404, detail="Vara não encontrada")
    return db_vara


@router.patch("/api/v1/varas/{vara_id}", response_model=VaraRead, tags=["Varas"])
async def atualizar_vara(
    vara_id: int,
    update: VaraUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Atualizar Vara."""
    db_vara = VaraService.atualizar(db, vara_id, update)
    if not db_vara:
        raise HTTPException(status_code=404, detail="Vara não encontrada")
    return db_vara


@router.delete("/api/v1/varas/{vara_id}", tags=["Varas"])
async def deletar_vara(
    vara_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Deletar Vara (soft delete)."""
    result = VaraService.deletar(db, vara_id)
    if not result:
        raise HTTPException(status_code=404, detail="Vara não encontrada")
    return {"ok": True, "message": "Vara deletada (inativada)"}


# ============== JUIZ ENDPOINTS ==============

@router.post("/api/v1/juizes", response_model=JuizRead, tags=["Juizes"])
async def criar_juiz(
    juiz: JuizCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Criar novo Juiz."""
    try:
        # Validar se Comarca existe
        comarca = ComarcaService.obter_por_id(db, juiz.comarca_id)
        if not comarca:
            raise HTTPException(status_code=404, detail="Comarca não encontrada")

        # Validar Vara se fornecida
        if juiz.vara_id:
            vara = VaraService.obter_por_id(db, juiz.vara_id)
            if not vara:
                raise HTTPException(status_code=404, detail="Vara não encontrada")

        db_juiz = JuizService.criar(db, juiz)
        return db_juiz
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/juizes", response_model=dict, tags=["Juizes"])
async def listar_juizes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    comarca_id: Optional[int] = Query(None),
    vara_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Listar Juizes com paginação."""
    total, items = JuizService.listar(db, comarca_id=comarca_id, vara_id=vara_id, skip=skip, limit=limit)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }


@router.get("/api/v1/juizes/{juiz_id}", response_model=JuizRead, tags=["Juizes"])
async def obter_juiz(
    juiz_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Obter Juiz por ID."""
    db_juiz = JuizService.obter_por_id(db, juiz_id)
    if not db_juiz:
        raise HTTPException(status_code=404, detail="Juiz não encontrado")
    return db_juiz


@router.patch("/api/v1/juizes/{juiz_id}", response_model=JuizRead, tags=["Juizes"])
async def atualizar_juiz(
    juiz_id: int,
    update: JuizUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Atualizar Juiz."""
    db_juiz = JuizService.atualizar(db, juiz_id, update)
    if not db_juiz:
        raise HTTPException(status_code=404, detail="Juiz não encontrado")
    return db_juiz


@router.delete("/api/v1/juizes/{juiz_id}", tags=["Juizes"])
async def deletar_juiz(
    juiz_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Deletar Juiz (soft delete)."""
    result = JuizService.deletar(db, juiz_id)
    if not result:
        raise HTTPException(status_code=404, detail="Juiz não encontrado")
    return {"ok": True, "message": "Juiz deletado (inativado)"}


# ============== PROCESSO ENDPOINTS ==============

@router.post("/api/v1/processos", response_model=ProcessoRead, tags=["Processos"])
async def criar_processo(
    processo: ProcessoCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Criar novo Processo.

    - **numero_cnj**: Número CNJ do processo (obrigatório)
    - **tipo**: Judicial ou Extrajudicial
    - **setor**: 01-Contábil, 02-Engenharia, etc.
    - **comarca_id**, **vara_id**, **juiz_id**: IDs das entidades judiciais
    - **responsavel_id**: ID do usuário responsável (opcional)
    """
    try:
        db_processo = ProcessoService.criar(db, processo)
        return db_processo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/processos", response_model=ProcessoListResponse, tags=["Processos"])
async def listar_processos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    comarca_id: Optional[int] = Query(None),
    juiz_id: Optional[int] = Query(None),
    responsavel_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Listar Processos com paginação e filtros.

    - **status**: Protocolado, Em Andamento, Concluído, Cancelado, Arquivado
    - **comarca_id**: Filtrar por Comarca
    - **juiz_id**: Filtrar por Juiz responsável
    - **responsavel_id**: Filtrar por usuário responsável
    """
    status_enum = None
    if status:
        try:
            status_enum = StatusProcesso(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Status inválido: {status}")

    total, items = ProcessoService.listar(
        db,
        skip=skip,
        limit=limit,
        status=status_enum,
        comarca_id=comarca_id,
        juiz_id=juiz_id,
        responsavel_id=responsavel_id,
    )
    return ProcessoListResponse(total=total, skip=skip, limit=limit, items=items)


@router.get("/api/v1/processos/{processo_id}", response_model=ProcessoRead, tags=["Processos"])
async def obter_processo(
    processo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Obter Processo por ID."""
    db_processo = ProcessoService.obter_por_id(db, processo_id)
    if not db_processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return db_processo


@router.patch("/api/v1/processos/{processo_id}", response_model=ProcessoRead, tags=["Processos"])
async def atualizar_processo(
    processo_id: int,
    update: ProcessoUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Atualizar Processo (partial update).

    Apenas os campos fornecidos serão atualizados.
    """
    try:
        db_processo = ProcessoService.atualizar(db, processo_id, update)
        if not db_processo:
            raise HTTPException(status_code=404, detail="Processo não encontrado")
        return db_processo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/v1/processos/{processo_id}", tags=["Processos"])
async def deletar_processo(
    processo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Deletar Processo (soft delete — marcar como cancelado)."""
    result = ProcessoService.deletar(db, processo_id)
    if not result:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return {"ok": True, "message": "Processo deletado (marcado como cancelado)"}


@router.get("/api/v1/processos/stats/dashboard", response_model=dict, tags=["Processos"])
async def processos_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Dashboard de Processos — contagem por status."""
    stats = ProcessoService.contar_por_status(db)
    return stats


# ============== PHASE 2: Incluir subrouters de Laudos + Financeiro ==============

if HAS_PHASE2:
    # Incluir routers Phase 2 (Laudos + Financeiro)
    # Nota: Estes routers já definem seu próprio prefix "/api/v1/..."
    router.include_router(laudos_phase2_router)
    router.include_router(financeiro_phase2_router)
