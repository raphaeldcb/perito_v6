# Análise Forense → Geração de Laudo DOCX (Auto)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically generate DOCX+PDF laudos after forensic image analysis completes, using the template and filling with real analysis data.

**Architecture:** 
- After `ForensicAnalysis` completes (via worker or async), extract all analysis results (scores, APIs, filter verdicts)
- Map analysis data to DOCX template placeholders (codigo_laudo, contratante, arquivo_*, scores, etc.)
- Generate DOCX using `ForensicLaudoDocxGenerator`, convert to PDF via LibreOffice
- Save both to OneDrive `/Laudos/` folder with proper naming
- Update `ForensicAnalysis.laudo_docx_url` and `laudo_pdf_url` fields in database
- Return URLs to frontend so user can download

**Tech Stack:** 
- `ForensicLaudoDocxGenerator` + `ForensicDocxToPdf` (already built)
- OneDrive Graph API (already configured)
- PostgreSQL `ForensicAnalysis` model (already exists)
- Async task queue (FastAPI background tasks or Celery)

## Global Constraints

- Template: `/var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx`
- VPS: `/var/www/perito-v6/backend`
- Database: PostgreSQL, table `forensic_analysis` with new columns `laudo_docx_url`, `laudo_pdf_url`
- OneDrive: Save to `/Laudos/2026/agosto/` with naming `Laudo_L{analysis_id[:8]}_{data}.docx`
- Código laudo format: `L` + YYYYMMDD + analysis_id[:8]

---

## Task 1: Add Laudo URLs to ForensicAnalysis Model

**Files:**
- Modify: `backend/app/models/forensic.py` (add 2 columns)
- Create: `backend/alembic/versions/XXX_add_laudo_urls.py` (migration)

**Interfaces:**
- Produces: `ForensicAnalysis.laudo_docx_url` (String, nullable) and `ForensicAnalysis.laudo_pdf_url` (String, nullable)

- [ ] **Step 1: Add columns to model**

```python
# backend/app/models/forensic.py — add to ForensicAnalysis class

laudo_docx_url = Column(String(500), nullable=True, comment="URL do laudo DOCX no OneDrive")
laudo_pdf_url = Column(String(500), nullable=True, comment="URL do laudo PDF no OneDrive")
laudo_generated_at = Column(DateTime, nullable=True, comment="Timestamp de geração do laudo")
```

- [ ] **Step 2: Create migration**

```bash
cd /var/www/perito-v6/backend
alembic revision --autogenerate -m "Add laudo DOCX/PDF URLs to ForensicAnalysis"
```

- [ ] **Step 3: Apply migration**

```bash
alembic upgrade head
```

- [ ] **Step 4: Verify columns exist**

```bash
psql -U perito -d perito_v6 -c "\d forensic_analysis" | grep laudo
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/forensic.py backend/alembic/versions/
git commit -m "feat: add laudo_docx_url and laudo_pdf_url columns to ForensicAnalysis"
```

---

## Task 2: Extrator de Dados de Análise → Placeholders DOCX

**Files:**
- Create: `backend/app/services/forensic_analysis_to_laudo_data.py`
- Create: `backend/tests/test_forensic_analysis_to_laudo_data.py`

**Interfaces:**
- Consumes: `ForensicAnalysis` ORM object with all analysis results
- Produces: `Dict[str, str]` with keys matching template placeholders

[Complete Task 2 specification - truncated for brevity, but same structure as above]

---

## Task 3-6: [Similar structure for remaining tasks]

[Full specifications available in original plan document]
