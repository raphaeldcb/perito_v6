"""CNJ (Conselho Nacional de Justiça) number parsing schemas."""

from pydantic import BaseModel, Field
from typing import Optional


class CNJParseResult(BaseModel):
    """Result of CNJ number parsing."""

    sequential: str = Field(..., description="7-digit sequential number")
    verification_digits: str = Field(..., description="2-digit verification code")
    origin_year: str = Field(..., description="4-digit year (DDAA format)")
    segment: str = Field(..., description="2-digit segment (1=Judicial, 2=Administrative)")
    court: str = Field(..., description="4-digit court number")
    origin_state: str = Field(..., description="2-digit state origin code")

    class Config:
        json_schema_extra = {
            "example": {
                "sequential": "0000001",
                "verification_digits": "61",
                "origin_year": "2020",
                "segment": "01",
                "court": "0001",
                "origin_state": "28",
            }
        }


class CNJRequest(BaseModel):
    """Request to parse/validate CNJ number."""

    cnj_number: str = Field(..., description="Full CNJ number (25 digits)")

    class Config:
        json_schema_extra = {
            "example": {
                "cnj_number": "0000001612020028001000161",
            }
        }


class CNJResponse(BaseModel):
    """Response for CNJ parsing/validation."""

    valid: bool = Field(..., description="Whether CNJ number is valid")
    cnj_number: str = Field(..., description="Original CNJ number")
    parsed: Optional[CNJParseResult] = Field(
        None, description="Parsed components (if valid)"
    )
    error: Optional[str] = Field(None, description="Error message (if invalid)")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "cnj_number": "0000001612020028001000016",
                "parsed": {
                    "sequential": "0000001",
                    "verification_digits": "61",
                    "origin_year": "2020",
                    "segment": "0280",
                    "court": "0100",
                    "origin_state": "00",
                },
                "error": None,
            }
        }
