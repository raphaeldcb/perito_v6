"""Schemas for padroes de cálculo (pattern calculation)."""

from pydantic import BaseModel, Field


class AplicarPadraoInput(BaseModel):
    """Input payload for applying a calculation pattern to a process."""
    padrao_id: int = Field(..., description="ID of the pattern to apply")
    processo_id: int = Field(..., description="ID of the process")

    class Config:
        json_schema_extra = {
            "example": {
                "padrao_id": 1,
                "processo_id": 42,
            }
        }


class AplicarPadraoResponse(BaseModel):
    """Response from applying a calculation pattern."""
    job_id: int = Field(..., description="Background job ID")
    status: str = Field(..., description="Current status")
    mensagem: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": 123,
                "status": "interpretando_decisao_oficial",
                "mensagem": "Buscando PDF da decisão nos autos...",
            }
        }
