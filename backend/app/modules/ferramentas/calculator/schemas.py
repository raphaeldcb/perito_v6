"""Calculator request/response schemas for deslocamento and juros."""

from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class DeslocamentoRequest(BaseModel):
    """Request for deslocamento (travel expense) calculation."""

    distance_km: float = Field(..., gt=0, description="Distance in kilometers")
    toll_cost: float = Field(default=0, ge=0, description="Toll cost in R$")
    rate_per_km: Optional[float] = Field(
        default=2.50,
        gt=0,
        description="Rate per kilometer in R$ (default: 2.50)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "distance_km": 150.5,
                "toll_cost": 45.80,
                "rate_per_km": 2.50,
            }
        }


class DeslocamentoResponse(BaseModel):
    """Response for deslocamento calculation."""

    distance_km: float = Field(..., description="Distance in kilometers")
    toll_cost: float = Field(..., description="Toll cost in R$")
    rate_per_km: float = Field(..., description="Rate per kilometer in R$")
    travel_cost: float = Field(..., description="Travel cost (distance × rate)")
    total_cost: float = Field(..., description="Total cost (travel + toll)")

    class Config:
        json_schema_extra = {
            "example": {
                "distance_km": 150.5,
                "toll_cost": 45.80,
                "rate_per_km": 2.50,
                "travel_cost": 376.25,
                "total_cost": 422.05,
            }
        }


class JurosRequest(BaseModel):
    """Request for juros (interest) calculation."""

    principal: Decimal = Field(..., gt=0, description="Principal amount in R$")
    rate_per_month: float = Field(
        default=0.01, ge=0, description="Monthly interest rate (0.01 = 1%)"
    )
    days: int = Field(..., gt=0, description="Number of days")

    class Config:
        json_schema_extra = {
            "example": {
                "principal": "1000.00",
                "rate_per_month": 0.01,
                "days": 90,
            }
        }


class JurosResponse(BaseModel):
    """Response for juros calculation."""

    principal: Decimal = Field(..., description="Principal amount in R$")
    rate_per_month: float = Field(..., description="Monthly interest rate")
    days: int = Field(..., description="Number of days")
    interest_amount: Decimal = Field(..., description="Calculated interest in R$")
    total_amount: Decimal = Field(..., description="Total (principal + interest)")

    class Config:
        json_schema_extra = {
            "example": {
                "principal": "1000.00",
                "rate_per_month": 0.01,
                "days": 90,
                "interest_amount": "30.00",
                "total_amount": "1030.00",
            }
        }


class CalculatorResponse(BaseModel):
    """Generic calculator response wrapper."""

    success: bool = Field(..., description="Whether calculation succeeded")
    data: Optional[dict] = Field(None, description="Calculation result")
    error: Optional[str] = Field(None, description="Error message if failed")
