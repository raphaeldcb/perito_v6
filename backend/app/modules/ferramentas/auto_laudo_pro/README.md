# AutoLaudoPro — Isolated Judicial Laudo Auto-Generation Tool

**Status**: ✅ Complete and Isolated  
**Version**: 1.0.0  
**Created**: 2026-08-12  

---

## Overview

AutoLaudoPro is a **completely isolated, modular tool** for automated judicial laudo (expert report) generation. It:

- **Extracts structured data** from judicial process documents using Qwen 3.6 (local, free)
- **Performs OCR** on PDFs/images (OCRmyPDF or Qwen vision fallback)
- **Fills templates** with extracted data
- **Indexes generated laudos** in RAG (pgvector) for semantic search
- **Validates quality** with efficiency metrics (fill rate, confidence scores)

**Key principle**: Zero dependencies on other ferramentas modules. Plug-and-play integration via FastAPI routers.

---

## Architecture

### Isolation Strategy

```
auto_laudo_pro/
├── __init__.py          # Public exports (schemas + router only)
├── schemas.py           # Pydantic DTOs (request/response)
├── service.py           # Business logic (stateless, singleton)
└── router.py            # FastAPI endpoints

Dependencies:
✓ app.config.settings    # Global settings (Ollama URL, etc.)
✓ app.database           # DB session for RAG indexing
✓ app.shared.schemas     # ApiResponse, ErrorDetail (standard DTOs)
✓ app.services.rag_indexer  # RAG chunk storage (optional)

✗ NO imports from:
  - app.modules.ferramentas.calculator
  - app.modules.ferramentas.cnj
  - app.modules.ferramentas.*  (other modules)
```

### Data Flow

```
1. USER UPLOADS DOCUMENT
   POST /api/v1/auto-laudo/extrair
   └─> ProcessUploadRequest (file_content, file_type, tipo_pericia)

2. OCR PIPELINE
   service.ocr_documento()
   ├─> Try OCRmyPDF (if installed)
   ├─> Fallback to Qwen vision
   └─> Return extracted_text, was_ocr_applied

3. DATA EXTRACTION
   service.extrair_dados_processo(extracted_text)
   ├─> Call Qwen via Ollama
   ├─> Parse JSON response
   └─> Return ExtractionData + metrics

4. VALIDATION
   service.validar_eficiencia(extraction)
   ├─> Count filled fields → fill_rate
   ├─> Check critical fields
   └─> Calculate quality_score (0.0-1.0)

5. TEMPLATE FILLING (OPTIONAL)
   POST /api/v1/auto-laudo/gerar
   service.aplicar_template(extraction, template_text)
   └─> Replace {{placeholders}} in template

6. RAG INDEXING (OPTIONAL)
   service.alimentar_rag(db, laudo_content, laudo_id)
   ├─> Chunk laudo (512 chars, 50 overlap)
   ├─> Embed each chunk (nomic-embed-text via Ollama)
   └─> Store in documento_rag table

7. VALIDATION CHECK
   GET /api/v1/auto-laudo/validar/{job_id}
   └─> Return ValidarEficienciaResponse with all metrics
```

---

## API Endpoints

### 1. Extract Process Data

**Endpoint**: `POST /api/v1/auto-laudo/extrair`

**Request**:
```json
{
  "file_content": "base64_encoded_pdf_or_text...",
  "file_type": "PDF|TXT|DOCX|IMAGE",
  "file_name": "processo_2025_001.pdf",
  "tipo_pericia": "Contábil",
  "padroes_ids": [1, 2]
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "extraction_id": "ext_abc12345",
    "extracted_data": {
      "Numero_Laudo": "LAU-2025-001",
      "Autos": "1234567890123",
      "Requerente": "John Doe",
      "Requerido": "Jane Doe",
      "Objeto": "Dispute resolution",
      ...
    },
    "extraction_confidence": 0.92,
    "fill_rate": 0.87,
    "field_confidence": {
      "Requerente": 0.95,
      "Objeto": 0.78,
      ...
    },
    "ocr_applied": true,
    "processing_time_ms": 2450
  }
}
```

**Fields Extracted** (see `ExtractionData` schema):
- Core: Numero_Laudo, Autos, Origem, Requerente, Requerido, Objeto
- Appointment: Nomeacao_Data, Nomeacao_Fls, Autoridade, Inicio_Data, Inicio_Hora, Inicio_Tipo
- Honoraries: Honorarios_Tipo, Honorarios_Valor, Honorarios_Homologacao_Data, Honorarios_Homologacao_Fls
- Judicial Decision: Decisao_Fls, Decisao_Citacao, Extrato_Fls, Diferenca_Valor, Saldo_Credor, Saldo_Credor_Extenso
- Questionnaires: Quesitos_Detalhados (with Juizo, Requerente, Requerido groups and responses)
- Custom: Campos_Personalizados (flexible per expertise type)

---

### 2. Generate Laudo from Extraction

**Endpoint**: `POST /api/v1/auto-laudo/gerar`

**Request** (form data):
```
extraction_id: "ext_abc12345"
extraction_data_json: '{"Numero_Laudo": "...", ...}'
template_id: 1 (optional)
file_format: "txt|docx|pdf" (default: txt)
```

**Response**:
```json
{
  "success": true,
  "data": {
    "laudo_id": "laud_def45678",
    "laudo_content": "LAUDO PERICIAL Nº LAU-2025-001\n...",
    "template_used": "template_1",
    "extraction_id": "ext_abc12345",
    "indexed_chunks": 12,
    "rag_ids": [1001, 1002, 1003, ...],
    "generation_confidence": 0.88,
    "processing_time_ms": 3200,
    "file_format": "txt",
    "file_url": "/api/v1/auto-laudo/download/laud_def45678"
  }
}
```

---

### 3. Validate Extraction Quality

**Endpoint**: `GET /api/v1/auto-laudo/validar/{job_id}`

**Response**:
```json
{
  "success": true,
  "data": {
    "job_id": "ext_abc12345",
    "status": "success|partial|failed",
    "extraction_success": true,
    "laudo_generated": true,
    "fill_rate": 0.92,
    "extraction_confidence": 0.89,
    "rag_indexed": true,
    "indexed_chunks": 15,
    "warnings": [
      "Saldo_Credor_Extenso was auto-generated",
      "Some optional fields missing"
    ],
    "errors": [],
    "quality_score": 0.88,
    "timestamp": "2025-08-12T12:34:56Z"
  }
}
```

---

## Configuration

Set these environment variables in `.env`:

```bash
# Ollama (Qwen model)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=perito-qwen

# OCR (optional)
OCR_ENGINE=ocrmypdf  # or "qwen_vision" for fallback

# RAG (optional)
RAG_EMBED_MODEL=nomic-embed-text
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=50
```

---

## Usage Examples

### Example 1: Extract from Uploaded PDF

```python
import requests
import base64

# Read PDF and encode
with open("processo_2025.pdf", "rb") as f:
    pdf_base64 = base64.b64encode(f.read()).decode()

# Call extraction
response = requests.post(
    "http://localhost:8000/api/v1/auto-laudo/extrair",
    json={
        "file_content": pdf_base64,
        "file_type": "PDF",
        "file_name": "processo_2025.pdf",
        "tipo_pericia": "Contábil",
    }
)

extraction = response.json()["data"]
print(f"Extracted {extraction['fill_rate']*100:.0f}% of fields")
print(f"Confidence: {extraction['extraction_confidence']*100:.0f}%")
```

### Example 2: Generate Laudo from Extraction

```python
import json

# Use extraction data from previous step
extraction_data = extraction["extracted_data"]

# Generate laudo
response = requests.post(
    "http://localhost:8000/api/v1/auto-laudo/gerar",
    data={
        "extraction_id": extraction["extraction_id"],
        "extraction_data_json": json.dumps(extraction_data),
        "template_id": None,  # Use default template
        "file_format": "txt",
    }
)

laudo = response.json()["data"]
print(f"Generated laudo {laudo['laudo_id']}")
print(f"Indexed {laudo['indexed_chunks']} chunks in RAG")

# Save laudo content
with open("laudo_output.txt", "w") as f:
    f.write(laudo["laudo_content"])
```

### Example 3: Check Quality

```python
# Validate extraction
response = requests.get(
    f"http://localhost:8000/api/v1/auto-laudo/validar/{extraction['extraction_id']}"
)

validation = response.json()["data"]
if validation["quality_score"] < 0.70:
    print("⚠️ Low quality extraction — manual review recommended")
    print(f"Warnings: {validation['warnings']}")
else:
    print("✓ High quality extraction")
```

---

## Testing

### Run isolation tests

```bash
cd v6/backend
pytest tests/modules/ferramentas/test_auto_laudo_pro_isolation.py -v
```

**Tests verify**:
1. ✓ Module imports without other ferramentas dependencies
2. ✓ Schemas are properly defined
3. ✓ Service methods work (mocked external calls)
4. ✓ Router endpoints are defined
5. ✓ No breaking changes to existing ferramentas

### Verify no cross-module imports

```bash
grep -r "from app.modules.ferramentas\." \
  app/modules/ferramentas/auto_laudo_pro/*.py | grep -v "^.*#"
# Should return 0 results
```

### Run existing tests (regression)

```bash
pytest tests/modules/test_cnj.py -v      # Calculator tests
pytest tests/modules/test_calculator.py -v  # CNJ parsing tests
```

---

## Implementation Details

### OCR Pipeline

1. **TXT files**: Return as-is (already text)
2. **PDF/Image**:
   - Try OCRmyPDF (Linux/macOS, requires installation)
   - Fallback to Qwen vision (via Ollama)
3. **DOCX**: Extract text via python-docx
4. **Other**: Error

### Data Extraction

- Uses Qwen 3.6 via Ollama (local, no API keys)
- Prompts specifically designed for judicial processes
- Extracts ~20-25 core fields + unlimited custom fields
- Parses JSON response (markdown code block or raw object)
- Validates critical fields (Autos, Requerente, Requerido, etc.)

### Quality Metrics

- **fill_rate**: % of non-empty fields (0.0-1.0)
- **field_confidence**: Per-field scores (dict[str, float])
- **quality_score**: Weighted score (0.6 × fill_rate + 0.4 × critical_rate)
- **warnings**: Missing critical fields, low fill rate, etc.

### RAG Indexing

- Chunks laudo in 512-char blocks (50-char overlap)
- Embeds via nomic-embed-text (768-dim, Ollama)
- Stores in `documento_rag` table with origin='laudo'
- Enables semantic search of generated laudos

---

## Future Enhancements

### Phase 1: Job Persistence
- [ ] Store extraction/laudo jobs in DB
- [ ] Track job status (queued, processing, completed, failed)
- [ ] Retrieve job results by ID

### Phase 2: Custom Templates
- [ ] UI for uploading custom templates (.docx, .txt)
- [ ] Template versioning
- [ ] Placeholder validation (check template has required fields)

### Phase 3: Batch Processing
- [ ] Upload multiple documents
- [ ] Extract + generate laudos in parallel
- [ ] Batch export (ZIP)

### Phase 4: Output Formats
- [ ] DOCX generation (python-docx templates)
- [ ] PDF generation (DOCX → PDF conversion)
- [ ] Signature placeholder support

### Phase 5: Advanced RAG
- [ ] Query similar laudos
- [ ] Context-aware laudo suggestions
- [ ] Cross-case pattern detection

---

## Troubleshooting

### "Qwen returned empty response"
- Check Ollama is running: `curl http://localhost:11434/api/generate`
- Check model is loaded: `ollama list | grep perito-qwen`

### "Could not parse JSON from Qwen response"
- Qwen may have hallucinated or returned invalid JSON
- Try shortening input document (max ~50k chars)
- Check Qwen temperature (0.1-0.3 recommended for extraction)

### "OCR failed for PDF"
- Check OCRmyPDF is installed: `which ocrmypdf`
- Check PDF is readable (not corrupted)
- Fallback to Qwen vision (slower but always works)

### "RAG indexing failed"
- Check PostgreSQL is running and pgvector extension is installed
- RAG indexing is optional — laudo generation still works without it

---

## Code Organization

```
auto_laudo_pro/
├── __init__.py
│   └── Exports: schemas (DTO), router (FastAPI), docstring (this file)
│
├── schemas.py
│   ├── ExtractionData          # Complete extracted fields
│   ├── QuesitosAgrupados       # Grouped questionnaires + answers
│   ├── ProcessUploadRequest    # Upload request DTO
│   ├── ExtracaoResponse        # Extraction response DTO
│   ├── LaudoGeradoResponse     # Laudo generation response DTO
│   └── ValidarEficienciaResponse  # Validation response DTO
│
├── service.py
│   ├── AutoLaudoProService
│   │   ├── ocr_documento()     # PDF/image → text
│   │   ├── extrair_dados_processo()  # Text → structured data (Qwen)
│   │   ├── validar_eficiencia()  # Quality validation
│   │   ├── aplicar_template()  # Fill template with data
│   │   └── alimentar_rag()     # Index in pgvector
│   └── get_auto_laudo_service()  # Singleton getter
│
└── router.py
    ├── POST /extrair           # Extract data
    ├── POST /gerar             # Generate laudo
    ├── GET /validar/{job_id}   # Validate
    └── GET /download/{laudo_id}  # Download (TODO)
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| OCR PDF | <5s | Varies by page count; Qwen vision slower |
| Extraction | <10s | Qwen 3.6 on decent hardware |
| Template filling | <500ms | Fast string replacement |
| RAG indexing | <2s | 512-char chunks + embeddings |
| Total E2E | <30s | All steps serial |

---

## Support & Maintenance

- **Module owner**: AutoLaudoPro team
- **Maintenance**: Verify tests pass after updates
- **Dependencies**: Qwen 3.6 (Ollama), OCRmyPDF (optional), pgvector (optional)
- **Backward compatibility**: Schemachanges require migration; routers can be updated

---

## License & Attribution

- Extracted logic from AIStudio laudo generation system
- Adapted for isolated Perito v6 modular architecture
- Local Qwen replacement for Google Gemini (free alternative)

---

**Last updated**: 2026-08-12  
**Status**: ✅ Ready for integration testing
