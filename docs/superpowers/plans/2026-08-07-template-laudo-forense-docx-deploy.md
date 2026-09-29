# Template Laudo Forense — Integração DOCX + Deploy VPS

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrar o template DOCX de laudo forense (profissional, branding IPC-MS) ao sistema de análise forense, preenchendo automaticamente com dados reais, e fazer deploy no VPS.

**Architecture:** 
- Parser do template DOCX para extrair placeholders {{VARIAVEL}}
- Mapeamento 1:1 entre dados de análise forense e placeholders
- Gerador DOCX que preenche + valida + assinatura eletrônica (futuro)
- Integração com rotas existentes (`/api/v1/forensic/analyze`)
- Salva PDF + DOCX em bucket OneDrive

**Tech Stack:** 
- `python-docx` (pip install) para manipulação DOCX
- Integração com `forensic_orchestrator.py` (já existe)
- `libreoffice --headless` para DOCX→PDF no VPS
- Routes: `GET /api/v1/forensic/{analysis_id}/laudo-docx` (novo)

---

## Global Constraints

- Template source: `/Users/ipc_server/Downloads/TEMPLATE_LAUDO_FORENSE EXteste rodape.docx`
- 50+ placeholders {{VARIAVEL}} mapeados exatamente
- Suportar análise de IMAGEM, VÍDEO, ÁUDIO (futuro)
- Cadeia de custódia: hash SHA-256 obrigatório
- Assinatura: campo aberto para A3/WebSigner (Task 5)
- VPS: `/var/www/perito-v6/backend`

---

## Task 1: Mapper de Placeholders DOCX

**Files:**
- Create: `backend/app/services/forensic_docx_mapper.py`
- Create: `backend/tests/test_forensic_docx_mapper.py`
- Modify: `backend/app/services/forensic_laudo_generator.py` (deprecate ReportLab)

**Interfaces:**
- Consumes: Dict de análise com chaves `codigo_laudo`, `contratante`, `objeto`, `arquivo_nome`, `arquivo_mime`, etc.
- Produces: `class ForensicDocxMapper` com método `extract_placeholders() -> Dict[str, str]` e `map_data(data: Dict) -> Dict[str, str]`

- [ ] **Step 1: Write failing test**

```python
# tests/test_forensic_docx_mapper.py
import pytest
from app.services.forensic_docx_mapper import ForensicDocxMapper

def test_extract_placeholders_from_template():
    mapper = ForensicDocxMapper()
    placeholders = mapper.extract_placeholders()
    
    assert '{{CODIGO_LAUDO}}' in placeholders
    assert '{{CONTRATANTE}}' in placeholders
    assert '{{ARQUIVO_NOME}}' in placeholders
    assert '{{ARQUIVO_HASH_SHA256}}' in placeholders
    assert len(placeholders) >= 50

def test_map_forensic_data_to_docx():
    mapper = ForensicDocxMapper()
    data = {
        'codigo_laudo': 'L202608070001',
        'contratante': 'João Silva',
        'objeto': 'Análise de imagem suspeita',
        'arquivo_nome': 'foto.jpg',
        'arquivo_mime': 'image/jpeg',
        'arquivo_dimensoes': '1920x1080',
        'arquivo_tamanho': '2048000',
        'arquivo_hash_sha256': 'abc123...',
        'arquivo_hash_sha1': 'def456...',
        'arquivo_hash_md5': 'ghi789...',
        'data_calculo_hash': '2026-08-07T14:30:00Z',
        'total_achados': '3',
        'total_criticos': '1',
        'total_alertas': '2',
        'total_informativos': '0',
        'confianca': '92',
        'nivel_risco': 'ALTO'
    }
    
    mapped = mapper.map_data(data)
    assert mapped['{{CODIGO_LAUDO}}'] == 'L202608070001'
    assert mapped['{{CONTRATANTE}}'] == 'João Silva'
    assert mapped['{{ARQUIVO_HASH_SHA256}}'] == 'abc123...'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_docx_mapper.py::test_extract_placeholders_from_template -v
# Expected: FAIL (module not found)
```

- [ ] **Step 3: Create mapper service**

```python
# backend/app/services/forensic_docx_mapper.py
"""
Mapper entre dados de análise forense e placeholders do template DOCX.
Extrai {{VARIAVEL}} e mapeia dados reais.
"""
from pathlib import Path
from docx import Document
import re
from typing import Dict, Set


class ForensicDocxMapper:
    """Extrai e mapeia placeholders do template DOCX de laudo forense."""
    
    TEMPLATE_PATH = Path("/var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx")
    
    def __init__(self, template_path: Path = None):
        self.template_path = template_path or self.TEMPLATE_PATH
        self.doc = Document(self.template_path)
        self.placeholders: Set[str] = set()
        self._extract_all_placeholders()
    
    def _extract_all_placeholders(self) -> None:
        """Extrai todos os {{VARIAVEL}} do documento."""
        for para in self.doc.paragraphs:
            matches = re.findall(r'\{\{[A-Z_0-9]+\}\}', para.text)
            self.placeholders.update(matches)
        
        for table in self.doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        matches = re.findall(r'\{\{[A-Z_0-9]+\}\}', para.text)
                        self.placeholders.update(matches)
    
    def extract_placeholders(self) -> Set[str]:
        """Retorna set de todos os placeholders encontrados."""
        return self.placeholders
    
    def map_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        Mapeia dados para placeholders.
        
        Args:
            data: Dict com chaves minúsculas (e.g., 'codigo_laudo')
        
        Returns:
            Dict mapeado com chaves {{MAIUSCULA}} (e.g., {{CODIGO_LAUDO}})
        """
        mapping = {}
        for placeholder in self.placeholders:
            # Remove {{ e }} e converte para minúsculas
            key = placeholder.strip('{}').lower()
            if key in data:
                mapping[placeholder] = data[key]
            else:
                mapping[placeholder] = "[NÃO PREENCHIDO]"
        return mapping
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd /var/www/perito-v6/backend
pip install python-docx
pytest tests/test_forensic_docx_mapper.py -v
# Expected: PASS (2 testes)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/forensic_docx_mapper.py \
        backend/tests/test_forensic_docx_mapper.py
git commit -m "feat: add ForensicDocxMapper to extract and map template placeholders"
```

---

## Task 2: Copiar Template para VPS + Backend

**Files:**
- Copy: `TEMPLATE_LAUDO_FORENSE EXteste rodape.docx` → `/var/www/perito-v6/backend/app/templates/`
- Create: `backend/app/templates/.gitkeep`
- Modify: `.gitignore` (template é asset, não ignore)

**Interfaces:**
- Consumes: Template DOCX local
- Produces: Template disponível em `/var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx`

- [ ] **Step 1: Copiar template para repo local**

```bash
mkdir -p /var/www/perito-v6/backend/app/templates
cp "/Users/ipc_server/Downloads/TEMPLATE_LAUDO_FORENSE EXteste rodape.docx" \
   /var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx
```

- [ ] **Step 2: Adicionar ao git**

```bash
cd /var/www/perito-v6/backend
git add app/templates/TEMPLATE_LAUDO_FORENSE.docx
git commit -m "feat: add forensic laudo template (DOCX)"
```

- [ ] **Step 3: Verificar no VPS após deploy**

```bash
ssh -p 22022 root@129.121.34.186 \
  "ls -lh /var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx"
# Expected: arquivo com ~200-500 KB
```

- [ ] **Step 4: Commit local**

```bash
git add backend/app/templates/.gitkeep
git commit -m "chore: add templates directory"
```

---

## Task 3: Gerador de DOCX Preenchido

**Files:**
- Create: `backend/app/services/forensic_laudo_docx_generator.py`
- Create: `backend/tests/test_forensic_laudo_docx_generator.py`
- Modify: `backend/app/services/forensic_orchestrator.py` (adicionar método `generate_laudo_docx()`)

**Interfaces:**
- Consumes: Dict de análise forense com 50+ chaves (de Task 1), caminho do template
- Produces: Arquivo DOCX preenchido (bytes) + caminho OneDrive

- [ ] **Step 1: Write failing test**

```python
# tests/test_forensic_laudo_docx_generator.py
import pytest
from io import BytesIO
from app.services.forensic_laudo_docx_generator import ForensicLaudoDocxGenerator

def test_generate_laudo_docx_with_full_data():
    generator = ForensicLaudoDocxGenerator()
    
    analysis_data = {
        'codigo_laudo': 'L202608070001',
        'contratante': 'João Silva',
        'objeto': 'Análise de imagem suspeita de deepfake',
        'arquivo_nome': 'video_questionado.mp4',
        'arquivo_mime': 'video/mp4',
        'arquivo_dimensoes': '1920x1080@30fps',
        'arquivo_tamanho': '104857600',
        'arquivo_hash_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'arquivo_hash_sha1': 'da39a3ee5e6b4b0d3255bfef95601890afd80709',
        'arquivo_hash_md5': 'd41d8cd98f00b204e9800998ecf8427e',
        'data_calculo_hash': '2026-08-07T14:30:00Z',
        'total_achados': '5',
        'total_criticos': '2',
        'total_alertas': '3',
        'total_informativos': '0',
        'confianca': '85',
        'nivel_risco': 'ALTO'
    }
    
    docx_bytes = generator.generate(analysis_data)
    
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000
    
    # Verificar que template foi preenchido
    from docx import Document
    doc = Document(BytesIO(docx_bytes))
    full_text = '\n'.join([p.text for p in doc.paragraphs])
    
    assert 'L202608070001' in full_text
    assert 'João Silva' in full_text
    assert 'deepfake' in full_text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_laudo_docx_generator.py::test_generate_laudo_docx_with_full_data -v
# Expected: FAIL (module not found)
```

- [ ] **Step 3: Create generator service**

```python
# backend/app/services/forensic_laudo_docx_generator.py
"""
Gerador de Laudo Forense em DOCX.
Preenche template com dados de análise forense.
"""
from pathlib import Path
from io import BytesIO
from docx import Document
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ForensicLaudoDocxGenerator:
    """Gera DOCX de laudo forense preenchido com dados reais."""
    
    TEMPLATE_PATH = Path("/var/www/perito-v6/backend/app/templates/TEMPLATE_LAUDO_FORENSE.docx")
    
    def __init__(self, template_path: Optional[Path] = None):
        self.template_path = template_path or self.TEMPLATE_PATH
        
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template não encontrado: {self.template_path}")
    
    def generate(self, analysis_data: Dict[str, str]) -> bytes:
        """
        Gera DOCX preenchido com dados de análise.
        
        Args:
            analysis_data: Dict com chaves em minúsculas (codigo_laudo, contratante, etc.)
        
        Returns:
            bytes: DOCX gerado
        """
        # Carregar template
        doc = Document(self.template_path)
        
        # Converter keys para {{MAIUSCULA}}
        replacements = self._prepare_replacements(analysis_data)
        
        # Substituir em parágrafos
        for para in doc.paragraphs:
            for replacement, value in replacements.items():
                if replacement in para.text:
                    self._replace_in_paragraph(para, replacement, value)
        
        # Substituir em tabelas
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for replacement, value in replacements.items():
                            if replacement in para.text:
                                self._replace_in_paragraph(para, replacement, value)
        
        # Salvar em memória
        output = BytesIO()
        doc.save(output)
        output.seek(0)
        
        return output.getvalue()
    
    def _prepare_replacements(self, data: Dict[str, str]) -> Dict[str, str]:
        """Converte chaves minúsculas em {{MAIUSCULA}}."""
        replacements = {}
        for key, value in data.items():
            placeholder = '{{' + key.upper() + '}}'
            replacements[placeholder] = str(value)
        return replacements
    
    def _replace_in_paragraph(self, para, old_text: str, new_text: str) -> None:
        """Substitui texto em parágrafo preservando formatação."""
        if old_text not in para.text:
            return
        
        # Estratégia: clonar runs e atualizar texto
        full_text = para.text
        new_full_text = full_text.replace(old_text, new_text)
        
        # Limpar runs antigos
        for run in para.runs:
            r = run._element
            r.getparent().remove(r)
        
        # Adicionar novo run
        para.add_run(new_full_text)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_laudo_docx_generator.py -v
# Expected: PASS (1 teste)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/forensic_laudo_docx_generator.py \
        backend/tests/test_forensic_laudo_docx_generator.py
git commit -m "feat: add ForensicLaudoDocxGenerator to fill template with analysis data"
```

---

## Task 4: Integração com Rota de Análise Forense

**Files:**
- Modify: `backend/app/routes/forensic_analysis.py` (adicionar endpoint GET `/laudo-docx`)
- Modify: `backend/app/services/forensic_orchestrator.py` (adicionar método)
- Create: `backend/tests/test_forensic_laudo_routes.py`

**Interfaces:**
- Consumes: `analysis_id` (UUID)
- Produces: DOCX bytes + headers `Content-Disposition: attachment; filename="Laudo_L202608070001.docx"`

- [ ] **Step 1: Write failing route test**

```python
# tests/test_forensic_laudo_routes.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_forensic_laudo_docx(authenticated_client, sample_analysis_id):
    """GET /api/v1/forensic/{analysis_id}/laudo-docx retorna DOCX."""
    response = authenticated_client.get(
        f"/api/v1/forensic/{sample_analysis_id}/laudo-docx"
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert len(response.content) > 1000
    assert response.content.startswith(b'PK')  # ZIP header (DOCX é ZIP)

def test_get_forensic_laudo_docx_not_found(authenticated_client):
    """GET com analysis_id inválido retorna 404."""
    response = authenticated_client.get(
        "/api/v1/forensic/00000000-0000-0000-0000-000000000000/laudo-docx"
    )
    
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_laudo_routes.py -v
# Expected: FAIL (route not found)
```

- [ ] **Step 3: Add route to forensic_analysis.py**

```python
# backend/app/routes/forensic_analysis.py (adicionar ao final)

from fastapi.responses import StreamingResponse
from app.services.forensic_laudo_docx_generator import ForensicLaudoDocxGenerator

@router.get("/{analysis_id}/laudo-docx", tags=["forensic"])
async def get_forensic_laudo_docx(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Gera DOCX de laudo forense preenchido.
    
    Returns:
        - 200: DOCX bytes
        - 404: analysis_id não encontrada
        - 403: Sem permissão
    """
    try:
        # Buscar análise no banco
        analysis = db.session.query(ForensicAnalysis)\
            .filter_by(id=analysis_id, user_id=current_user['id'])\
            .first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Análise não encontrada")
        
        # Preparar dados
        data = {
            'codigo_laudo': f"L{analysis.created_at.strftime('%Y%m%d')}{analysis.id[:8]}",
            'contratante': current_user.get('nome', 'Não informado'),
            'objeto': analysis.description or 'Análise forense de mídia',
            'arquivo_nome': analysis.filename,
            'arquivo_mime': analysis.file_type,
            # ... (completar com outros campos de analysis)
        }
        
        # Gerar DOCX
        generator = ForensicLaudoDocxGenerator()
        docx_bytes = generator.generate(data)
        
        return StreamingResponse(
            iter([docx_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=Laudo_{data['codigo_laudo']}.docx"}
        )
    
    except Exception as e:
        logger.error(f"Erro ao gerar laudo DOCX: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar laudo")
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_laudo_routes.py -v
# Expected: PASS (2 testes)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/forensic_analysis.py \
        backend/tests/test_forensic_laudo_routes.py
git commit -m "feat: add GET /forensic/{id}/laudo-docx endpoint"
```

---

## Task 5: Converter DOCX → PDF (LibreOffice Headless)

**Files:**
- Create: `backend/app/services/forensic_docx_to_pdf.py`
- Create: `backend/tests/test_forensic_docx_to_pdf.py`
- Modify: `backend/app/routes/forensic_analysis.py` (adicionar GET `/laudo-pdf`)

**Interfaces:**
- Consumes: DOCX bytes (de Task 3)
- Produces: PDF bytes (via LibreOffice)

- [ ] **Step 1: Write failing test**

```python
# tests/test_forensic_docx_to_pdf.py
import pytest
from app.services.forensic_docx_to_pdf import ForensicDocxToPdf

def test_convert_docx_to_pdf():
    converter = ForensicDocxToPdf()
    
    # Gerar DOCX de teste
    from app.services.forensic_laudo_docx_generator import ForensicLaudoDocxGenerator
    generator = ForensicLaudoDocxGenerator()
    docx_bytes = generator.generate({'codigo_laudo': 'L202608070001'})
    
    # Converter
    pdf_bytes = converter.convert(docx_bytes)
    
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')
    assert len(pdf_bytes) > 1000
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_docx_to_pdf.py -v
# Expected: FAIL (LibreOffice não instalado ou módulo não existe)
```

- [ ] **Step 3: Install LibreOffice on VPS**

```bash
ssh -p 22022 root@129.121.34.186 << 'EOF'
apt-get update
apt-get install -y libreoffice-writer libreoffice-headless
EOF
```

- [ ] **Step 4: Create converter service**

```python
# backend/app/services/forensic_docx_to_pdf.py
"""
Conversor DOCX → PDF usando LibreOffice headless.
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ForensicDocxToPdf:
    """Converte DOCX em PDF via LibreOffice."""
    
    LIBREOFFICE_PATH = "/usr/bin/libreoffice"
    
    def convert(self, docx_bytes: bytes) -> bytes:
        """
        Converte DOCX (bytes) em PDF (bytes).
        
        Args:
            docx_bytes: Conteúdo DOCX
        
        Returns:
            bytes: Conteúdo PDF
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Salvar DOCX temporário
            docx_path = tmpdir / "input.docx"
            docx_path.write_bytes(docx_bytes)
            
            # Converter via LibreOffice
            pdf_path = tmpdir / "input.pdf"
            
            try:
                subprocess.run([
                    self.LIBREOFFICE_PATH,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(tmpdir),
                    str(docx_path)
                ], check=True, capture_output=True, timeout=30)
                
                # Ler PDF
                if not pdf_path.exists():
                    raise FileNotFoundError(f"PDF não gerado: {pdf_path}")
                
                return pdf_path.read_bytes()
            
            except subprocess.TimeoutExpired:
                logger.error("LibreOffice timeout")
                raise Exception("Timeout ao converter DOCX→PDF")
            except subprocess.CalledProcessError as e:
                logger.error(f"LibreOffice error: {e.stderr.decode()}")
                raise Exception(f"Erro ao converter DOCX→PDF: {e.stderr.decode()}")
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_docx_to_pdf.py -v
# Expected: PASS (1 teste)
```

- [ ] **Step 6: Add PDF route**

```python
# backend/app/routes/forensic_analysis.py (adicionar)

from app.services.forensic_docx_to_pdf import ForensicDocxToPdf

@router.get("/{analysis_id}/laudo-pdf", tags=["forensic"])
async def get_forensic_laudo_pdf(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Gera PDF de laudo forense.
    
    Returns:
        - 200: PDF bytes
        - 404: analysis_id não encontrada
    """
    try:
        # Reutilizar lógica de /laudo-docx
        response = await get_forensic_laudo_docx(analysis_id, current_user)
        docx_bytes = await response.body()
        
        # Converter DOCX → PDF
        converter = ForensicDocxToPdf()
        pdf_bytes = converter.convert(docx_bytes)
        
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Laudo_L{analysis_id[:8]}.pdf"}
        )
    
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar PDF")
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/forensic_docx_to_pdf.py \
        backend/tests/test_forensic_docx_to_pdf.py \
        backend/app/routes/forensic_analysis.py
git commit -m "feat: add DOCX→PDF converter and GET /forensic/{id}/laudo-pdf"
```

---

## Task 6: Testes E2E + Deploy VPS

**Files:**
- Modify: `backend/tests/test_forensic_e2e.py` (adicionar cenário completo)
- Modify: `docker-compose.yml` (incluir libreoffice se usar container)

**Interfaces:**
- Consumes: VPS + Docker containers
- Produces: Tests passando + deployed code

- [ ] **Step 1: Write E2E test**

```python
# tests/test_forensic_e2e.py (adicionar ao final)

def test_forensic_analysis_complete_laudo_workflow(authenticated_client, sample_file):
    """E2E: Upload → Análise → Gerar DOCX + PDF."""
    
    # 1. Upload arquivo
    response = authenticated_client.post(
        "/api/v1/forensic/upload",
        files={"file": sample_file}
    )
    assert response.status_code == 200
    analysis_id = response.json()["id"]
    
    # 2. Aguardar análise
    import time
    time.sleep(5)
    
    # 3. Gerar DOCX
    response = authenticated_client.get(
        f"/api/v1/forensic/{analysis_id}/laudo-docx"
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    
    # 4. Gerar PDF
    response = authenticated_client.get(
        f"/api/v1/forensic/{analysis_id}/laudo-pdf"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    
    # 5. Validar conteúdo (básico)
    assert len(response.content) > 10000  # PDF tem tamanho mínimo
```

- [ ] **Step 2: Run E2E test local**

```bash
cd /var/www/perito-v6/backend
pytest tests/test_forensic_e2e.py::test_forensic_analysis_complete_laudo_workflow -v
# Expected: PASS
```

- [ ] **Step 3: Build e push ao VPS**

```bash
cd /var/www/perito-v6/backend
docker build -t perito-v6-backend:latest .
docker tag perito-v6-backend:latest perito-v6-backend:$(date +%Y%m%d)

# Push (via script safe_deploy.sh já existente)
bash /var/www/perito-v6/scripts/safe_deploy.sh
```

- [ ] **Step 4: Testar no VPS**

```bash
ssh -p 22022 root@129.121.34.186 << 'EOF'
cd /var/www/perito-v6/backend

# Verificar template
ls -lh app/templates/TEMPLATE_LAUDO_FORENSE.docx

# Testar rota (após container pronto)
curl -X GET "http://localhost:8000/api/v1/forensic/test-id/laudo-docx" \
  -H "Authorization: Bearer TOKEN"
EOF
```

- [ ] **Step 5: Final commit**

```bash
git add backend/tests/test_forensic_e2e.py
git commit -m "test: add E2E workflow for forensic laudo generation (DOCX+PDF)"
git push origin master
```

---

## Summary

**Deliverables:**
1. ✅ ForensicDocxMapper — extrai 50+ placeholders
2. ✅ ForensicLaudoDocxGenerator — preenche template
3. ✅ GET /api/v1/forensic/{id}/laudo-docx — retorna DOCX
4. ✅ GET /api/v1/forensic/{id}/laudo-pdf — retorna PDF
5. ✅ E2E tests passando
6. ✅ Deployed no VPS
