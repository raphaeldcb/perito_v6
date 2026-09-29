"""
AutoLaudoPro request/response schemas.

Data extraction, template filling, and laudo generation for judicial processes.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal


class Quesito(BaseModel):
    """Single questionnaire item with question and answer."""
    pergunta: str = Field(..., description="Question text")
    resposta: str = Field(default="", description="Answer to question")
    numero: Optional[int] = Field(None, description="Question number (optional)")

    @field_validator('pergunta', mode='before')
    @classmethod
    def convert_texto_to_pergunta(cls, v, info):
        """Convert 'texto' field (from Qwen) to 'pergunta' if needed."""
        if isinstance(v, dict):
            # If v is a dict (shouldn't happen here, but safe)
            return v.get('texto', v.get('pergunta', ''))
        return v

    model_config = {"extra": "allow"}  # Allow 'texto' and 'numero' fields


class QuesitosAgrupados(BaseModel):
    """Structured questionnaire responses grouped by party."""

    # Accept both List[str] (legacy) and List[Union[str, Quesito, dict]] (new format from Qwen)
    Juizo: List[Union[str, Quesito, Dict[str, Any]]] = Field(default_factory=list, description="Court questions")
    Requerente: List[Union[str, Quesito, Dict[str, Any]]] = Field(default_factory=list, description="Plaintiff questions")
    Requerido: List[Union[str, Quesito, Dict[str, Any]]] = Field(default_factory=list, description="Defendant questions")
    Outros: Optional[List[Union[str, Quesito, Dict[str, Any]]]] = Field(None, description="Other questions")
    Respostas_Juizo: List[str] = Field(default_factory=list, description="Court question answers")
    Respostas_Requerente: List[str] = Field(default_factory=list, description="Plaintiff answers")
    Respostas_Requerido: List[str] = Field(default_factory=list, description="Defendant answers")
    Referencia_Juizo: str = Field(default="", description="Court reference page range")
    Referencia_Requerente: str = Field(default="", description="Plaintiff reference page range")
    Referencia_Requerido: str = Field(default="", description="Defendant reference page range")

    @field_validator('Juizo', 'Requerente', 'Requerido', 'Outros', mode='before')
    @classmethod
    def normalize_quesitos(cls, v):
        """Normalize quesito lists to handle dict format from Qwen."""
        if not isinstance(v, list):
            return v

        normalized = []
        for item in v:
            if isinstance(item, dict):
                # Convert Qwen format {numero, texto, resposta} → Quesito {pergunta, resposta}
                quesito_dict = {
                    'pergunta': item.get('texto', item.get('pergunta', '')),
                    'resposta': item.get('resposta', ''),
                    'numero': item.get('numero'),
                }
                normalized.append(Quesito(**quesito_dict))
            else:
                normalized.append(item)
        return normalized


class ExtractionData(BaseModel):
    """Complete extracted data from judicial process documents."""

    # Core process identification
    Numero_Laudo: str = Field(..., description="Report number")
    Autos: str = Field(..., description="Process number (CNJ standard)")
    Origem: str = Field(..., description="Court and jurisdiction")
    Requerente: str = Field(..., description="Plaintiff name")
    Requerido: str = Field(..., description="Defendant name")
    Objeto: str = Field(..., description="Case subject matter")

    # Appointment and commencement details
    Nomeacao_Data: str = Field(..., description="Appointment date (written out)")
    Nomeacao_Fls: str = Field(..., description="Appointment page reference")
    Nomeacao_Decisao_Fls: Optional[str] = Field(None, description="Appointment decision page reference")
    Autoridade: str = Field(..., description="Appointing authority")
    Inicio_Data: str = Field(..., description="Commencement date (written out)")
    Inicio_Hora: str = Field(..., description="Commencement time")
    Inicio_Tipo: str = Field(..., description="Commencement type")

    # Honoraries
    Honorarios_Tipo: str = Field(..., description="Honoraries type (provisional/definitive)")
    Honorarios_Valor: str = Field(..., description="Honoraries value with thousand separators")
    Honorarios_Homologacao_Data: str = Field(..., description="Honoraries homologation date (written out)")
    Honorarios_Homologacao_Fls: str = Field(..., description="Honoraries homologation page reference")
    Honorarios_Resumo_Final: str = Field(..., description="Final honoraries summary")

    # Judicial decision and calculations
    Decisao_Fls: Optional[str] = Field(None, description="Decision page reference")
    Decisao_Citacao: Optional[str] = Field(None, description="Literal citation of judicial criteria")
    Extrato_Fls: Optional[str] = Field(None, description="Bank statement page references")
    Diferenca_Valor: Optional[str] = Field(None, description="Calculated difference value with separators")
    Saldo_Credor: Optional[str] = Field(None, description="Creditor balance with thousand separators")
    Saldo_Credor_Extenso: Optional[str] = Field(None, description="Creditor balance in words (Portuguese)")
    Data_Base: Optional[str] = Field(None, description="Base date (month/year prior to laudo)")

    # Questionnaires
    Quesitos_Info: Optional[str] = Field(None, description="Summary of questionnaire and technical assistants")
    Quesitos_Resumo_Formatado: str = Field(default="", description="Formatted questionnaire summary")
    Quesitos_Detalhados: QuesitosAgrupados = Field(
        default_factory=QuesitosAgrupados, description="Detailed questionnaires by party"
    )

    # Additional fields
    Documentos_Faltantes: Optional[List[str]] = Field(default_factory=list, description="List of missing documents")
    Observacoes: Optional[str] = Field(None, description="Additional observations")
    Referencias_Rastreabilidade: List[str] = Field(
        default_factory=list, description="Traceability references (page numbers)"
    )

    # Custom fields (flexible per expertise type)
    Campos_Personalizados: Optional[Dict[str, str]] = Field(
        None, description="Custom fields per expertise type (accounting, electrical, etc.)"
    )

    @field_validator('Documentos_Faltantes', mode='before')
    @classmethod
    def normalize_docs_faltantes(cls, v):
        """Normalize Documentos_Faltantes to handle empty lists or None."""
        if not v:
            return []
        return v if isinstance(v, list) else [v]


class ProcessUploadRequest(BaseModel):
    """Request to upload and extract process data."""

    file_content: str = Field(..., description="Base64-encoded file content or raw text")
    file_type: str = Field(..., description="File type: PDF, TXT, DOCX, IMAGE")
    file_name: str = Field(..., description="Original file name")
    tipo_pericia: str = Field(
        default="Contábil",
        description="Expertise type (Contábil, Engenharia, DNA, etc.)",
    )
    padroes_ids: Optional[List[int]] = Field(None, description="Template pattern IDs to apply")

    class Config:
        json_schema_extra = {
            "example": {
                "file_content": "base64_encoded_pdf...",
                "file_type": "PDF",
                "file_name": "processo_2025_001.pdf",
                "tipo_pericia": "Contábil",
                "padroes_ids": [1, 2],
            }
        }


class ExtracaoResponse(BaseModel):
    """Response with extracted process data and metrics."""

    extraction_id: str = Field(..., description="Unique extraction ID for tracking")
    extracted_data: ExtractionData = Field(..., description="Extracted process data")
    extraction_confidence: float = Field(
        ..., description="Overall extraction confidence (0.0-1.0)", ge=0.0, le=1.0
    )
    fill_rate: float = Field(
        ..., description="Percentage of fields populated (0.0-1.0)", ge=0.0, le=1.0
    )
    field_confidence: Optional[Dict[str, float]] = Field(
        None, description="Per-field confidence scores"
    )
    ocr_applied: bool = Field(False, description="Whether OCR was applied to extract text")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "extraction_id": "ext_20250810_001",
                "extracted_data": {...},
                "extraction_confidence": 0.92,
                "fill_rate": 0.87,
                "field_confidence": {"Requerente": 0.95, "Objeto": 0.78},
                "ocr_applied": True,
                "processing_time_ms": 2450,
            }
        }


class LaudoGeradoResponse(BaseModel):
    """Response with generated laudo and indexing metrics."""

    laudo_id: str = Field(..., description="Unique laudo ID")
    laudo_content: str = Field(..., description="Generated laudo text")
    template_used: Optional[str] = Field(None, description="Template applied")
    extraction_id: Optional[str] = Field(None, description="Source extraction ID")
    indexed_chunks: int = Field(
        ..., description="Number of chunks indexed in RAG (pgvector)"
    )
    rag_ids: Optional[List[int]] = Field(None, description="Database IDs of indexed chunks")
    generation_confidence: float = Field(
        ..., description="Laudo generation confidence (0.0-1.0)", ge=0.0, le=1.0
    )
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    file_format: str = Field(default="txt", description="Output format: txt, docx, pdf")
    file_url: Optional[str] = Field(None, description="Download URL for generated laudo")

    class Config:
        json_schema_extra = {
            "example": {
                "laudo_id": "laud_20250810_001",
                "laudo_content": "LAUDO PERICIAL Nº ...",
                "template_used": "contabil_padrao",
                "extraction_id": "ext_20250810_001",
                "indexed_chunks": 12,
                "rag_ids": [1001, 1002, 1003],
                "generation_confidence": 0.88,
                "processing_time_ms": 3200,
                "file_format": "txt",
                "file_url": "/api/v1/auto-laudo/download/laud_20250810_001",
            }
        }


class ValidarEficienciaResponse(BaseModel):
    """Validation response with efficiency metrics."""

    job_id: str = Field(..., description="Job/extraction ID being validated")
    status: str = Field(..., description="Status: success, partial, failed")
    extraction_success: bool = Field(..., description="Whether extraction succeeded")
    laudo_generated: bool = Field(..., description="Whether laudo was generated")
    fill_rate: float = Field(..., description="Extraction field fill rate")
    extraction_confidence: float = Field(..., description="Extraction confidence score")
    rag_indexed: bool = Field(..., description="Whether laudo was indexed in RAG")
    indexed_chunks: int = Field(..., description="Number of RAG chunks created")
    warnings: List[str] = Field(default_factory=list, description="Warnings (missing fields, etc.)")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    quality_score: float = Field(
        ..., description="Overall quality score (0.0-1.0)", ge=0.0, le=1.0
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "ext_20250810_001",
                "status": "success",
                "extraction_success": True,
                "laudo_generated": True,
                "fill_rate": 0.92,
                "extraction_confidence": 0.89,
                "rag_indexed": True,
                "indexed_chunks": 15,
                "warnings": ["Saldo_Credor_Extenso was auto-generated"],
                "errors": [],
                "quality_score": 0.88,
                "timestamp": "2025-08-10T12:34:56Z",
            }
        }
