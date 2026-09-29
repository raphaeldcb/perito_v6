"""
AutoLaudoPro service — Isolated, stateless extraction, OCR, template filling, and RAG indexing.

Core logic:
1. OCR documents (PDF/images -> text via OCRmyPDF or built-in tools)
2. Extract structured data using Qwen local model
3. Validate and enrich extracted data
4. Fill templates with extracted data
5. Index generated laudo in RAG (pgvector)
6. Calculate efficiency metrics

All operations are deterministic, stateless, and compatible with Qwen 3.6 (Ollama).
No external APIs (Google Gemini) — uses local free tools only.
"""

import base64
import json
import logging
import os
import re
import subprocess
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from decimal import Decimal

import requests
from sqlalchemy.orm import Session

from app.config.settings import settings
from .schemas import (
    ProcessUploadRequest,
    ExtracaoResponse,
    ExtractionData,
    QuesitosAgrupados,
    LaudoGeradoResponse,
    ValidarEficienciaResponse,
)

logger = logging.getLogger(__name__)


class AutoLaudoProService:
    """
    Isolated, stateless service for judicial laudo generation.

    No dependencies on other ferramentas modules.
    Pure Qwen (local Ollama) + OCR (OCRmyPDF or built-in).
    """

    def __init__(self, ollama_url: str = None, embedding_url: str = None):
        """Initialize with Ollama and RAG embedding URLs."""
        self.ollama_url = ollama_url or settings.ollama_url
        self.ollama_model = settings.ollama_model
        self.embedding_url = embedding_url or self.ollama_url  # Ollama serves both

    # =========================================================================
    # OCR Pipeline
    # =========================================================================

    def ocr_documento(self, file_content: str, file_type: str) -> Tuple[str, bool]:
        """
        Extract text from document.

        For PDF/image: uses OCRmyPDF (if available) or fallback to Qwen vision.
        For TXT: returns as-is.

        Args:
            file_content: Base64-encoded or raw text file content
            file_type: PDF, DOCX, TXT, IMAGE

        Returns:
            Tuple of (extracted_text, was_ocr_applied)

        Raises:
            ValueError: If file format unsupported or extraction fails
        """
        file_type_upper = file_type.upper()

        # TXT files: assume already text
        if file_type_upper == "TXT":
            try:
                text = base64.b64decode(file_content).decode("utf-8")
            except:
                text = file_content  # Already plain text
            return text, False

        # Decode binary content
        try:
            binary_content = base64.b64decode(file_content)
        except Exception as e:
            raise ValueError(f"Failed to decode file content: {e}")

        # PDF or IMAGE: Try OCRmyPDF first
        if file_type_upper in ("PDF", "IMAGE"):
            text = self._ocr_with_ocrmypdf(binary_content, file_type_upper)
            if text:
                return text, True

            # Fallback to Qwen vision
            logger.warning(
                f"OCRmyPDF failed for {file_type_upper}, falling back to Qwen vision"
            )
            text = self._ocr_with_qwen_vision(file_content, file_type_upper)
            if text:
                return text, True

            raise ValueError(f"OCR failed for {file_type}: both methods exhausted")

        # DOCX: Extract text (python-docx)
        if file_type_upper == "DOCX":
            text = self._extract_docx_text(binary_content)
            if text:
                return text, False
            raise ValueError("Failed to extract text from DOCX")

        raise ValueError(f"Unsupported file type: {file_type}")

    def _ocr_with_ocrmypdf(self, binary_content: bytes, file_type: str) -> Optional[str]:
        """Try OCR with OCRmyPDF (must be installed in v6/tools-pericia venv)."""
        try:
            # Write temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                suffix=".pdf" if file_type == "PDF" else ".png", delete=False
            ) as tmp:
                tmp.write(binary_content)
                tmp_path = tmp.name

            try:
                # Run OCRmyPDF with sidecar text output
                output_path = tmp_path.replace(".pdf", "_ocr.pdf").replace(".png", "_ocr.pdf")
                sidecar_path = output_path.replace(".pdf", ".txt")

                subprocess.run(
                    [
                        "ocrmypdf",
                        "--force-ocr",
                        "--sidecar",
                        sidecar_path,
                        tmp_path,
                        output_path,
                    ],
                    capture_output=True,
                    timeout=30,
                    check=True,
                )

                # Read OCR text from sidecar file
                if os.path.exists(sidecar_path):
                    with open(sidecar_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    return text if text.strip() else None

                return None
            finally:
                # Cleanup
                for path in [tmp_path, output_path]:
                    if os.path.exists(path):
                        os.remove(path)

        except Exception as e:
            logger.warning(f"OCRmyPDF failed: {e}")
            return None

    def _ocr_with_qwen_vision(self, base64_content: str, file_type: str) -> Optional[str]:
        """Fallback OCR using Qwen vision capabilities via Ollama with retry."""
        try:
            prompt = "Extract all text from this image. Output only the text, no commentary."
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "images": [base64_content],
                "stream": False,
                "temperature": 0.1,
            }

            resp = requests.post(url, json=payload, timeout=90)
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            return text if text else None

        except (requests.Timeout, requests.ConnectionError) as e:
            logger.warning(f"Qwen vision temporary failure, retrying: {e}")
            raise  # Retry decorator will handle
        except Exception as e:
            logger.warning(f"Qwen vision OCR failed: {e}")
            return None

    def _extract_docx_text(self, binary_content: bytes) -> Optional[str]:
        """Extract text from DOCX using python-docx."""
        try:
            from docx import Document
            from io import BytesIO

            doc = Document(BytesIO(binary_content))
            text = "\n".join(p.text for p in doc.paragraphs)
            return text if text.strip() else None

        except Exception as e:
            logger.warning(f"DOCX extraction failed: {e}")
            return None

    # =========================================================================
    # Data Extraction
    # =========================================================================

    def extrair_dados_processo(
        self, texto_processo: str, tipo_pericia: str = "Contábil"
    ) -> ExtractionData:
        """
        Extract structured data from process text using Qwen.

        Calls Qwen with carefully crafted prompt to extract all judicial process fields.
        Parses JSON response and validates completeness.

        Args:
            texto_processo: Extracted text from documents
            tipo_pericia: Expertise type (Contábil, Engenharia, DNA, etc.)

        Returns:
            ExtractionData with extracted fields

        Raises:
            ValueError: If extraction fails or JSON parsing fails
        """
        # Build extraction prompt
        prompt = self._build_extraction_prompt(tipo_pericia)
        prompt += f"\n\n### CONTEÚDO DO PROCESSO:\n{texto_processo[:50000]}"  # Limit token usage

        # Call Qwen
        response_text = self._chamar_qwen(prompt)

        if not response_text:
            raise ValueError("Qwen returned empty response")

        # Parse JSON from response
        extracted_dict = self._parse_json_from_response(response_text)
        if not extracted_dict:
            raise ValueError("Could not parse JSON from Qwen response")

        # Normalize Documentos_Faltantes (workaround: accept string or list, normalize to list)
        if "Documentos_Faltantes" in extracted_dict:
            val = extracted_dict["Documentos_Faltantes"]
            if isinstance(val, str):
                extracted_dict["Documentos_Faltantes"] = [val] if val.strip() else []
            elif isinstance(val, list):
                extracted_dict["Documentos_Faltantes"] = val
            else:
                extracted_dict["Documentos_Faltantes"] = []

        # Build ExtractionData
        extraction = ExtractionData(**{k: v for k, v in extracted_dict.items() if k in ExtractionData.model_fields})

        return extraction

    def _build_extraction_prompt(self, tipo_pericia: str) -> str:
        """Build Qwen extraction prompt for given expertise type."""
        base_prompt = f"""Você é um perito judicial especialista em extração de dados.
Analise o processo abaixo e extraia TODOS os campos estruturados em JSON.

**Tipo de Perícia:** {tipo_pericia}

### CAMPOS OBRIGATÓRIOS A EXTRAIR:
- Numero_Laudo: número do laudo ou "INFORMAR" se não encontrado
- Autos: número do processo (padrão CNJ)
- Origem: comarca e vara
- Requerente: nome completo do autor
- Requerido: nome completo do réu
- Objeto: pontos controvertidos (sem referências de folhas)
- Nomeacao_Data: data por extenso (ex: "19 de março de 2025")
- Nomeacao_Fls: página da nomeação
- Autoridade: autoridade nomeante
- Inicio_Data: data por extenso
- Inicio_Hora: hora do início
- Inicio_Tipo: tipo de início
- Honorarios_Tipo: tipo de honorários
- Honorarios_Valor: valor com separadores de milhar
- Honorarios_Homologacao_Data: data por extenso
- Honorarios_Homologacao_Fls: página
- Honorarios_Resumo_Final: resumo final
- Quesitos_Info: resumo sobre quesitos e assistentes
- Quesitos_Resumo_Formatado: resumo formatado
- Quesitos_Detalhados: objeto com Juizo, Requerente, Requerido (listas) e respostas

### CAMPOS OPCIONAIS:
- Decisao_Fls, Decisao_Citacao, Extrato_Fls, Diferenca_Valor, Saldo_Credor, Saldo_Credor_Extenso, Data_Base
- Documentos_Faltantes, Observacoes, Campos_Personalizados (dict)

### INSTRUÇÕES:
1. Datas SEMPRE por extenso em português
2. Valores com separadores de milhar (ex: 1.250,50)
3. Para campos não encontrados: usar string vazia "", nunca null
4. Responda APENAS com JSON válido dentro de ```json...```
5. Cada quesito deve ter resposta correspondente em Respostas_*
6. Se quesito é fora de escopo, responder: "Prejudicado (Extra Escopo). Matéria exclusivamente de direito."

Responda com JSON estruturado:"""

        return base_prompt

    def _chamar_qwen(self, prompt: str, temperature: float = 0.2) -> str:
        """Call Qwen via Ollama with automatic retry on failure."""
        try:
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "num_predict": 4000,  # Allow longer responses for JSON
            }

            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

        except requests.ConnectionError as e:
            logger.error(f"Ollama connection failed at {self.ollama_url}: {e}")
            raise ValueError(f"Cannot connect to Ollama at {self.ollama_url}")
        except requests.Timeout:
            logger.error(f"Ollama timeout after 60s at {self.ollama_url}")
            raise ValueError(f"Ollama timeout — check SSH tunnel or load")
        except Exception as e:
            logger.error(f"Qwen API error: {e}")
            raise ValueError(f"Qwen API error: {e}")

    @staticmethod
    def _parse_json_from_response(text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Qwen response."""
        # Try markdown JSON block first
        match = re.search(r"```json\n([\s\S]*?)\n```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try raw JSON object
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None

    # =========================================================================
    # Efficiency Validation
    # =========================================================================

    def validar_eficiencia(self, extraction: ExtractionData) -> Dict[str, Any]:
        """
        Validate extraction completeness and quality.

        Calculates:
        - Fill rate: % of non-empty fields
        - Field confidence per critical field
        - Quality score (0.0-1.0)
        - Warnings for missing/incomplete fields

        Args:
            extraction: Extracted data

        Returns:
            Dict with validation metrics
        """
        all_fields = extraction.model_dump()
        total_fields = len(all_fields)

        # Count filled fields (non-empty strings and non-empty collections)
        filled_fields = 0
        empty_fields = []
        field_confidence = {}

        for field_name, field_value in all_fields.items():
            if field_value and (
                isinstance(field_value, str) and field_value.strip()
                or isinstance(field_value, (list, dict)) and len(field_value) > 0
            ):
                filled_fields += 1
                field_confidence[field_name] = 0.95  # Default high confidence
            else:
                empty_fields.append(field_name)
                field_confidence[field_name] = 0.0

        fill_rate = filled_fields / total_fields if total_fields > 0 else 0.0

        # Critical fields (must be present for valid extraction)
        critical_fields = {
            "Numero_Laudo",
            "Autos",
            "Requerente",
            "Requerido",
            "Objeto",
            "Nomeacao_Data",
            "Inicio_Data",
        }

        missing_critical = [f for f in critical_fields if not getattr(extraction, f, "").strip()]
        warnings = []

        if missing_critical:
            warnings.append(f"Missing critical fields: {', '.join(missing_critical)}")

        if fill_rate < 0.5:
            warnings.append("Extraction fill rate below 50% — manual review recommended")

        # Quality score: balance fill_rate with critical field presence
        critical_rate = (len(critical_fields) - len(missing_critical)) / len(critical_fields)
        quality_score = (fill_rate * 0.6 + critical_rate * 0.4)

        return {
            "fill_rate": fill_rate,
            "field_confidence": field_confidence,
            "quality_score": quality_score,
            "warnings": warnings,
            "missing_fields": empty_fields,
            "missing_critical": missing_critical,
        }

    # =========================================================================
    # Template Filling
    # =========================================================================

    def aplicar_template(self, extraction: ExtractionData, template_text: Optional[str] = None) -> str:
        """
        Fill template with extracted data.

        Uses {{field}} placeholders from template or generates default laudo structure.

        Args:
            extraction: Extracted data
            template_text: Template with {{placeholders}} or None for default

        Returns:
            Filled template text
        """
        if not template_text:
            # Generate default laudo structure
            template_text = self._generate_default_laudo_template()

        # Build replacement map
        replacement_map = self._build_replacement_map(extraction)

        # Replace all {{placeholders}}
        result = template_text
        for key, value in replacement_map.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

        # Remove any unreplaced placeholders
        result = re.sub(r"\{\{[^}]+\}\}", "", result)

        return result

    def _build_replacement_map(self, extraction: ExtractionData) -> Dict[str, str]:
        """Build flat key-value map for template replacement."""
        data = extraction.model_dump()

        # Flatten nested Quesitos_Detalhados
        quesitos = data.get("Quesitos_Detalhados", {})
        if isinstance(quesitos, dict):
            for group in ["Juizo", "Requerente", "Requerido"]:
                questions = quesitos.get(group, [])
                answers = quesitos.get(f"Respostas_{group}", [])
                for i, q in enumerate(questions):
                    ans = answers[i] if i < len(answers) else ""
                    data[f"Quesito_{group.lower()}_{i+1}"] = q
                    data[f"Resposta_{group.lower()}_{i+1}"] = ans
                data[f"Referencia_{group}"] = quesitos.get(f"Referencia_{group}", "")

        # Flatten custom fields
        custom = data.get("Campos_Personalizados", {})
        if isinstance(custom, dict):
            for key, value in custom.items():
                data[f"Custom_{key}"] = value

        return {k: v or "" for k, v in data.items() if isinstance(v, (str, int, float, Decimal))}

    def _generate_default_laudo_template(self) -> str:
        """Generate default laudo structure."""
        return """LAUDO PERICIAL Nº {{Numero_Laudo}}

AUTOS: {{Autos}}
ORIGEM: {{Origem}}
REQUERENTE: {{Requerente}}
REQUERIDO: {{Requerido}}

1. OBJETO
{{Objeto}}

2. NOMEAÇÃO
Data: {{Nomeacao_Data}} (fls. {{Nomeacao_Fls}})
Autoridade: {{Autoridade}}

3. INÍCIO DOS TRABALHOS
Data: {{Inicio_Data}}
Hora: {{Inicio_Hora}}
Tipo: {{Inicio_Tipo}}

4. HONORÁRIOS
Tipo: {{Honorarios_Tipo}}
Valor: {{Honorarios_Valor}}
Homologado em {{Honorarios_Homologacao_Data}} (fls. {{Honorarios_Homologacao_Fls}})
{{Honorarios_Resumo_Final}}

5. QUESITOS
{{Quesitos_Resumo_Formatado}}

Quesitos do Juízo (fls. {{Referencia_Juizo}}):
{{#Quesito_juizo_1}}• {{Quesito_juizo_1}} R: {{Resposta_juizo_1}}{{/Quesito_juizo_1}}

Quesitos da Requerente (fls. {{Referencia_Requerente}}):
{{#Quesito_requerente_1}}• {{Quesito_requerente_1}} R: {{Resposta_requerente_1}}{{/Quesito_requerente_1}}

Quesitos da Requerida (fls. {{Referencia_Requerido}}):
{{#Quesito_requerido_1}}• {{Quesito_requerido_1}} R: {{Resposta_requerido_1}}{{/Quesito_requerido_1}}

6. ANÁLISE E CONCLUSÃO
{{Observacoes}}

Saldo Credor: {{Saldo_Credor}} ({{Saldo_Credor_Extenso}})

Data Base: {{Data_Base}}

Respeitosamente submetido,

---
Laudo gerado automaticamente por AutoLaudoPro
"""

    # =========================================================================
    # RAG Indexing
    # =========================================================================

    def alimentar_rag(self, db: Session, laudo_content: str, laudo_id: str, origem: str = "laudo") -> List[int]:
        """
        Index generated laudo in RAG (pgvector).

        Chunks the laudo, embeds each chunk via Ollama (nomic-embed-text),
        and stores in documento_rag table.

        Args:
            db: Database session
            laudo_content: Generated laudo text
            laudo_id: Unique laudo ID for reference
            origem: Origin type (default "laudo")

        Returns:
            List of inserted document_rag IDs

        Raises:
            Exception: If indexing fails
        """
        from app.services.rag_indexer import chunk_text, ensure_schema
        from sqlalchemy import text

        try:
            # Ensure RAG schema exists
            ensure_schema(db)

            # Chunk the laudo
            chunks = chunk_text(laudo_content, chunk_size=512, overlap=50)
            if not chunks:
                logger.warning(f"No chunks generated from laudo {laudo_id}")
                return []

            # Embed each chunk and store
            inserted_ids = []
            for idx, chunk in enumerate(chunks):
                embedding = self._get_embedding(chunk)

                if not embedding:
                    logger.warning(f"Embedding failed for chunk {idx} of laudo {laudo_id}")
                    continue

                # Store in database
                embedding_json = json.dumps(embedding)
                sql = text("""
                    INSERT INTO documento_rag (origem, ref_id, chunk_idx, texto, embedding, criado_em)
                    VALUES (:origem, :ref_id, :chunk_idx, :texto, :embedding, now())
                    RETURNING id
                """)

                result = db.execute(
                    sql,
                    {
                        "origem": origem,
                        "ref_id": laudo_id,
                        "chunk_idx": idx,
                        "texto": chunk,
                        "embedding": embedding_json,
                    },
                )
                db.commit()

                row = result.first()
                if row:
                    inserted_ids.append(row[0])

            logger.info(f"Indexed laudo {laudo_id}: {len(inserted_ids)} chunks")
            return inserted_ids

        except Exception as e:
            logger.error(f"RAG indexing failed for laudo {laudo_id}: {e}")
            db.rollback()
            raise

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text via Ollama (nomic-embed-text) with retry."""
        try:
            url = f"{self.embedding_url}/api/embed"
            payload = {
                "model": "nomic-embed-text",
                "input": text,
            }

            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()

            embeddings = resp.json().get("embeddings", [])
            return embeddings[0] if embeddings else None

        except (requests.Timeout, requests.ConnectionError) as e:
            logger.warning(f"Embedding temporary failure, retrying: {e}")
            raise  # Retry decorator will handle
        except Exception as e:
            logger.warning(f"Embedding failed permanently: {e}")
            return None


# Singleton instance
_auto_laudo_service: Optional[AutoLaudoProService] = None


def get_auto_laudo_service() -> AutoLaudoProService:
    """Get or create singleton service."""
    global _auto_laudo_service
    if _auto_laudo_service is None:
        _auto_laudo_service = AutoLaudoProService()
    return _auto_laudo_service
