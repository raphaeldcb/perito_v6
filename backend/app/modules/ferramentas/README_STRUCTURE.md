# Ferramentas Module - Isolated Structure

## Overview

The `ferramentas` module organizes all specialized tools (features) for the Perito v6 system in isolated, self-contained folders. Each tool is completely independent with its own routing, schemas, and business logic.

## Folder Structure

```
v6/backend/app/modules/ferramentas/
├── cnj/                      # CNJ consultation tool
├── calculator/               # Calculation/math tool
├── fake_detector/            # Fake media detection (images/audio/video)
├── forensic/                 # Digital forensics analysis
├── deslocamento/             # Travel distance calculation
├── engenharia/               # Engineering expertise tool
├── dna/                      # DNA/biological analysis
├── diario/                   # Legal journal (DJEN) monitoring
├── cerebro/                  # Intelligence/AI coordination
├── rag/                      # Vector search/RAG (pgvector)
├── padroes/                  # Pattern recognition/analysis
├── conciliacao/              # Reconciliation/conciliation tool
├── coletador/                # Data collection tool
├── banco/                    # Bank data and financial operations
├── intimacoes/               # Court notifications/intimations
├── fluxo_honorarios/         # Honorarium flow management
├── dashboard_alertas/        # Alerts and dashboard
└── README_STRUCTURE.md       # This file
```

## File Structure Per Tool

Each tool folder contains exactly this structure:

```
{tool_name}/
├── __init__.py       # Exports router and schemas
├── router.py         # FastAPI routes (import router here)
├── schemas.py        # Pydantic models (import *  from here)
└── service.py        # Business logic (pure functions, classes)
```

### __init__.py

```python
from .router import router
from .schemas import *

__all__ = ["router"]
```

This ensures the tool's router is easily importable from the parent module.

### router.py

Contains FastAPI routes:

```python
from fastapi import APIRouter, Depends
from .schemas import SomeRequest, SomeResponse
from .service import some_business_logic

router = APIRouter()

@router.post("/endpoint")
async def endpoint_name(req: SomeRequest) -> SomeResponse:
    return some_business_logic(req)
```

Naming convention for routers:
- Prefix: `/api/v1/{tool_name}/`
- Example: `/api/v1/fake-detector/analyze`

### schemas.py

Contains all Pydantic models for request/response:

```python
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    url: str
    model: str

class AnalyzeResponse(BaseModel):
    is_fake: bool
    confidence: float
```

### service.py

Pure business logic, no FastAPI imports:

```python
from .schemas import AnalyzeRequest, AnalyzeResponse

def analyze_media(req: AnalyzeRequest) -> AnalyzeResponse:
    # Logic here - completely testable without FastAPI
    pass
```

## Loading Tool Routers

All tool routers are loaded in `v6/backend/app/main.py`:

```python
from fastapi import FastAPI
from app.modules.ferramentas import (
    fake_detector, forensic, deslocamento, engenharia,
    dna, diario, cerebro, rag, padroes, conciliacao,
    coletador, banco, intimacoes, fluxo_honorarios, dashboard_alertas,
    cnj, calculator
)

app = FastAPI()

# Register all tool routers
app.include_router(fake_detector.router, prefix="/api/v1/fake-detector")
app.include_router(forensic.router, prefix="/api/v1/forensic")
app.include_router(deslocamento.router, prefix="/api/v1/deslocamento")
# ... etc
```

## Adding a New Tool

To add a new tool, follow these steps:

1. **Create folder structure:**
   ```bash
   mkdir -p v6/backend/app/modules/ferramentas/{tool_name}
   ```

2. **Create files from template:**
   - Copy `__init__.py` template
   - Create empty `router.py`, `schemas.py`, `service.py`

3. **Implement the tool:**
   - Define request/response models in `schemas.py`
   - Implement business logic in `service.py`
   - Create FastAPI routes in `router.py`

4. **Register in main.py:**
   ```python
   from app.modules.ferramentas import {tool_name}
   app.include_router({tool_name}.router, prefix="/api/v1/{tool_name}")
   ```

5. **Test:**
   - Unit test `service.py` functions
   - Integration test routes in `router.py`

## Benefits of This Structure

1. **Isolation:** Each tool is completely independent
2. **Scalability:** New tools added without touching existing code
3. **Testing:** Business logic in `service.py` is pure functions (easy to test)
4. **Maintainability:** Clear separation of concerns
5. **Reusability:** Services can be used by other tools
6. **DDD:** Follows domain-driven design with each tool as a bounded context

## Migration Plan

Current state: Folder structure created (empty)
Next steps (subsequent tasks):
1. Move existing routes from `v6/backend/app/routes/` to respective tool folders
2. Extract schemas into `schemas.py` files
3. Extract business logic into `service.py` files
4. Update `main.py` to load all tool routers
5. Test all endpoints still work
6. Remove deprecated `routes/` folder

## Notes

- Do NOT modify `main.py` yet (done in later task)
- Do NOT move files in this task (isolation setup only)
- Each tool is independent - changes don't affect others
- All tools follow the same structure for consistency
