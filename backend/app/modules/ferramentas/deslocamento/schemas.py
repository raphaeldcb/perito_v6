"""
Schemas for deslocamento (travel distance/displacement) tools.

Includes models for:
- Input/output for route calculation (carro vs avião)
- Input/output for toll calculation (RotasBrasil API)
"""

from pydantic import BaseModel, Field
from typing import Optional


class DeslocamentoInput(BaseModel):
    """Input for travel distance calculation."""
    origem: str = Field(..., description="Origin city/address (e.g., 'Curitiba,PR' or '88525-600')")
    destino: str = Field(..., description="Destination city/address (e.g., 'Florianópolis,SC' or '88015-100')")
    ida_volta: bool = Field(default=True, description="Round trip or one-way")
    pedagio_manual: Optional[float] = Field(
        default=None,
        description="Manual toll value in BRL. If None, calculates automatically"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "origem": "Curitiba,PR",
                "destino": "Florianópolis,SC",
                "ida_volta": True,
                "pedagio_manual": None
            }
        }


class DeslocamentoResponse(BaseModel):
    """Response for travel distance calculation."""
    distancia_km: float = Field(..., description="Total distance in kilometers")
    tempo_horas: float = Field(..., description="Total travel time in hours")
    pedagio: float = Field(..., description="Toll amount in BRL")
    custo_total: float = Field(..., description="Total travel cost in BRL")
    detalhes: dict = Field(..., description="Additional details (origin, destination, polyline, mode)")
    comparativo: Optional[dict] = Field(
        default=None,
        description="Comparison with flight option (if distance > 600km)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "distancia_km": 800.0,
                "tempo_horas": 12.5,
                "pedagio": 150.0,
                "custo_total": 1110.0,
                "detalhes": {
                    "origem": "Curitiba,PR",
                    "destino": "Florianópolis,SC",
                    "ida_volta": True,
                    "custo_km": 960.0,
                    "polyline": "...",
                    "modo": "comparativo"
                },
                "comparativo": {
                    "carro": {
                        "distancia_km": 800.0,
                        "tempo_horas": 12.5,
                        "pedagio": 150.0,
                        "custo_km": 960.0,
                        "custo_total": 1110.0,
                        "moeda": "BRL",
                        "tipo": "ida e volta"
                    },
                    "aviao": {
                        "distancia_km": 400.0,
                        "tempo_horas": 4.2,
                        "preco_por_passageiro": 800.0,
                        "pedagio": 0.0,
                        "moeda": "BRL",
                        "tipo": "ida e volta",
                        "nota": "Preço estimado - consultar Google Flights para preço atualizado",
                        "economia_tempo": "8.3h menos"
                    },
                    "recomendacao": "carro",
                    "economia": {
                        "se_carro": "Economiza R$ 0.00 vs avião",
                        "se_aviao": "Economiza 8.3h vs carro"
                    }
                }
            }
        }


class PedagioInput(BaseModel):
    """Input for toll calculation via RotasBrasil API."""
    origem: str = Field(..., description="Origin city/address (e.g., 'Curitiba,PR' or '88525-600')")
    destino: str = Field(..., description="Destination city/address (e.g., 'Florianópolis,SC')")
    veiculo: str = Field(
        default="caminhao",
        description="Vehicle type: caminhao, onibus, carro, moto"
    )
    eixos: int = Field(
        default=6,
        ge=2,
        le=6,
        description="Number of axles (2-6)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "origem": "Curitiba,PR",
                "destino": "Florianópolis,SC",
                "veiculo": "caminhao",
                "eixos": 6
            }
        }


class PedagioResponse(BaseModel):
    """Response for toll calculation."""
    pedagio_total: float = Field(..., description="Total toll amount (round trip)")
    ida: float = Field(..., description="One-way toll amount")
    volta: float = Field(..., description="Return toll amount")
    distancia_km: int = Field(..., description="Distance in kilometers")
    tempo_viagem: str = Field(..., description="Travel time estimate")
    pontos: str = Field(..., description="Route points used")

    class Config:
        json_schema_extra = {
            "example": {
                "pedagio_total": 300.0,
                "ida": 150.0,
                "volta": 150.0,
                "distancia_km": 412,
                "tempo_viagem": "4h30m",
                "pontos": "Curitiba,PR;Florianópolis,SC"
            }
        }
