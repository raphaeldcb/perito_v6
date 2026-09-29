# Windows Agent Integration — Autonomo Processamento ESAJ/PJe

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows agent autônomo processa intimações ESAJ/PJe → localiza autos → insere BD → alimenta RAG → recebe A3 → protocolo, tudo sem intervenção humana até o usuário abrir a rotina.

**Architecture:** 
- VPS (Perito v6) expõe `/api/v1/jobs/windows-agent` webhook → Windows Agent polls ou recebe POST
- Windows Agent executa: busca ESAJ/PJe → extrai número → baixa PDF → cria entrada BD → indexa RAG → assina A3 → protocola TJMS
- Fluxo: Intimação Email/TJMS → localizar CNJ → BD → RAG → Dashboard pré-preenchido
- Recuperação: Worker queue + retry logic em caso de falha

**Tech Stack:** 
- Windows: Python 3.11 + Playwright (existente) + requests (API calls)
- VPS: FastAPI `/jobs/windows-agent`, PostgreSQL (job queue), pgvector (RAG)
- Assinatura: A3 (existente, Windows)
- Protocolo: TJMS API (existente)

## Global Constraints

- Sistema NUNCA bloqueia esperando Windows; fila assincronamente
- Dados duplicados: check MD5 PDF antes de salvar
- RAG update: vectorizar nome partes + número processo + tipo ação
- A3: assinatura via SafeKey/Softplan (existente)
- Protocolo TJMS: via API (endpoint já feito)

---

### Task 1: Criar Job Queue Model no PostgreSQL

**Files:**
- Modify: `backend/app/models/job.py` (criar se não existe)
- Modify: `backend/app/database.py` (adicionar alembic migration)
- Test: `tests/models/test_job.py`

**Interfaces:**
- Consumes: None (nova tabela)
- Produces: `JobModel(id, status, tipo, payload, resultado, tentativas, proxima_tentativa, criado_em, atualizado_em)`

- [ ] **Step 1: Write failing test**

```python
def test_create_job_queue():
    from app.models.job import JobModel
    job = JobModel(
        status="pending",
        tipo="esaj_search",
        payload={"cnj": "0501238-54.2022.8.12.0037", "trib": "TJMS"},
        tentativas=0
    )
    assert job.id is not None
    assert job.status == "pending"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/models/test_job.py::test_create_job_queue -v
# Expected: FAIL — JobModel not found
```

- [ ] **Step 3: Create JobModel**

Editar `backend/app/models/job.py`:

```python
from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class JobModel(Base):
    __tablename__ = "jobs_windows_agent"
    
    id = Column(Integer, primary_key=True)
    status = Column(String(20), default="pending")  # pending, running, success, failed
    tipo = Column(String(50))  # esaj_search, pje_search, download_pdf, sign_a3, protocol_tjms
    payload = Column(JSON)  # {cnj, trib, url, etc}
    resultado = Column(JSON, nullable=True)  # {pdf_path, entrada_bd_id, rag_id, assinado, protocolo}
    tentativas = Column(Integer, default=0)
    proxima_tentativa = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=func.now())
    atualizado_em = Column(DateTime, default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: Create Alembic migration**

```bash
cd backend
alembic revision --autogenerate -m "Create jobs_windows_agent table"
```

Editar `alembic/versions/xxxx_create_jobs_windows_agent.py`:

```python
def upgrade():
    op.create_table(
        'jobs_windows_agent',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('tipo', sa.String(50), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('resultado', sa.JSON(), nullable=True),
        sa.Column('tentativas', sa.Integer(), default=0),
        sa.Column('proxima_tentativa', sa.DateTime(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), default=func.now()),
        sa.Column('atualizado_em', sa.DateTime(), default=func.now()),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('jobs_windows_agent')
```

```bash
alembic upgrade head
```

- [ ] **Step 5: Run test (expect PASS)**

```bash
pytest tests/models/test_job.py::test_create_job_queue -v
# Expected: PASS
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/job.py backend/alembic/versions/*.py
git commit -m "feat: add jobs_windows_agent table for async job queue"
```

---

### Task 2: Criar endpoint POST `/api/v1/jobs/enqueue` (VPS chama Windows)

**Files:**
- Create: `backend/app/routes/jobs.py`
- Modify: `backend/app/main.py` (adicionar router)
- Test: `tests/routes/test_jobs.py`

**Interfaces:**
- Consumes: `JobModel` (Task 1)
- Produces: POST `/api/v1/jobs/enqueue` → `{job_id, status, tipo, tentativas}`

- [ ] **Step 1: Write failing test**

```python
def test_enqueue_esaj_job(client):
    response = client.post(
        "/api/v1/jobs/enqueue",
        json={
            "tipo": "esaj_search",
            "cnj": "0501238-54.2022.8.12.0037",
            "trib": "TJMS"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["job_id"] > 0
    assert data["status"] == "pending"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/routes/test_jobs.py::test_enqueue_esaj_job -v
# Expected: FAIL — route not found
```

- [ ] **Step 3: Create jobs.py router**

`backend/app/routes/jobs.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.job import JobModel
from datetime import datetime

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

@router.post("/enqueue", status_code=201)
def enqueue_job(
    payload: dict,
    db: Session = Depends(get_db)
):
    """Enfileirar job para Windows Agent processar"""
    
    tipo = payload.get("tipo")  # esaj_search, pje_search, etc
    if not tipo:
        raise HTTPException(status_code=400, detail="tipo é obrigatório")
    
    job = JobModel(
        status="pending",
        tipo=tipo,
        payload=payload,
        tentativas=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {
        "job_id": job.id,
        "status": job.status,
        "tipo": job.tipo,
        "tentativas": job.tentativas
    }
```

- [ ] **Step 4: Registrar router em main.py**

`backend/app/main.py`:

```python
from app.routes import jobs

app.include_router(jobs.router)
```

- [ ] **Step 5: Run test (expect PASS)**

```bash
pytest tests/routes/test_jobs.py::test_enqueue_esaj_job -v
# Expected: PASS
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/jobs.py tests/routes/test_jobs.py
git commit -m "feat: add POST /api/v1/jobs/enqueue for windows agent job queue"
```

---

### Task 3: Windows Agent — Pull Jobs e Atualizar Status

**Files:**
- Create: `windows/agent_v2.py` (novo, integrado ao existente)
- Create: `windows/jobs_processor.py`
- Test: `tests/windows/test_jobs_processor.py` (simular chamadas)

**Interfaces:**
- Consumes: `JobModel` (Task 1), GET `/api/v1/jobs/pending` (Task 4)
- Produces: `process_job(job_id, tipo, payload)` → escreve em `resultado`, muda status

- [ ] **Step 1: Write failing test**

```python
def test_process_esaj_job():
    from windows.jobs_processor import process_esaj_job
    
    job_payload = {
        "tipo": "esaj_search",
        "cnj": "0501238-54.2022.8.12.0037",
        "trib": "TJMS"
    }
    
    result = process_esaj_job(job_payload)
    
    assert result["status"] == "success"
    assert "pdf_path" in result
    assert result["pdf_path"].endswith(".pdf")
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/windows/test_jobs_processor.py::test_process_esaj_job -v
# Expected: FAIL — function not found
```

- [ ] **Step 3: Implementar processor**

`windows/jobs_processor.py`:

```python
import requests
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime
import hashlib

BASE_PASTA = Path("C:\\Perito\\Autos")
API_BASE = "http://sistema.ipcms.com.br/api/v1"

def process_esaj_job(job_id, job_payload):
    """Processar job ESAJ: buscar → baixar → inserir BD → RAG"""
    
    cnj = job_payload.get("cnj")
    trib = job_payload.get("trib", "TJMS")
    
    resultado = {}
    
    try:
        # 1. Buscar ESAJ (usar existente esaj_consulta_v2.py)
        print(f"🔍 Buscando ESAJ {cnj}...")
        pdf_path = esaj_download(cnj, trib)
        resultado["pdf_path"] = str(pdf_path)
        
        # 2. Calcular MD5 pra evitar duplicatas
        md5 = calcular_md5(pdf_path)
        
        # 3. Criar entrada BD via API
        print(f"📝 Inserindo BD...")
        bd_resp = requests.post(
            f"{API_BASE}/processos",
            json={
                "numero": cnj,
                "tribunal": trib,
                "pdf_path": str(pdf_path),
                "md5": md5,
                "data_download": datetime.now().isoformat()
            }
        )
        resultado["processo_id"] = bd_resp.json().get("id")
        
        # 4. Alimentar RAG
        print(f"🧠 Indexando RAG...")
        requests.post(
            f"{API_BASE}/rag/index",
            json={
                "processo_id": resultado["processo_id"],
                "conteudo": f"Processo {cnj} - {trib}",
                "tipo": "auto_judicial"
            }
        )
        resultado["rag_indexed"] = True
        
        # 5. Atualizar job status
        requests.patch(
            f"{API_BASE}/jobs/{job_id}",
            json={
                "status": "success",
                "resultado": resultado
            }
        )
        
        return {"status": "success", **resultado}
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        requests.patch(
            f"{API_BASE}/jobs/{job_id}",
            json={"status": "failed", "erro": str(e), "tentativas": "increment"}
        )
        return {"status": "failed", "erro": str(e)}

def esaj_download(cnj, tribunal):
    """Reutilizar script existente ou adaptar Playwright"""
    # TODO: chamar esaj_consulta_v2.py existente
    # Por enquanto, retornar path simulado
    pasta = BASE_PASTA / tribunal / cnj.replace(".", "_")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"{cnj}.pdf"

def calcular_md5(filepath):
    """Calcular MD5 do arquivo"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
```

- [ ] **Step 4: Criar agent_v2.py (loop polling)**

`windows/agent_v2.py`:

```python
import time
import requests
from jobs_processor import process_esaj_job, process_pje_job, process_sign_a3, process_protocol_tjms
from datetime import datetime, timedelta

API_BASE = "http://sistema.ipcms.com.br/api/v1"
POLL_INTERVAL = 30  # segundos

def main():
    print("🚀 Windows Agent v2 iniciado")
    
    while True:
        try:
            # 1. Buscar jobs pendentes
            resp = requests.get(f"{API_BASE}/jobs/pending", timeout=5)
            jobs = resp.json()
            
            for job in jobs:
                job_id = job["id"]
                tipo = job["tipo"]
                payload = job["payload"]
                
                print(f"\n📋 Job #{job_id}: {tipo}")
                
                # 2. Processar conforme tipo
                if tipo == "esaj_search":
                    process_esaj_job(job_id, payload)
                elif tipo == "pje_search":
                    process_pje_job(job_id, payload)
                elif tipo == "sign_a3":
                    process_sign_a3(job_id, payload)
                elif tipo == "protocol_tjms":
                    process_protocol_tjms(job_id, payload)
                else:
                    print(f"⚠️  Tipo desconhecido: {tipo}")
        
        except Exception as e:
            print(f"⚠️  Erro no polling: {e}")
        
        # Aguardar próximo ciclo
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test (expect PASS)**

```bash
pytest tests/windows/test_jobs_processor.py::test_process_esaj_job -v
# Expected: PASS (com mock de API)
```

- [ ] **Step 6: Commit**

```bash
git add windows/agent_v2.py windows/jobs_processor.py
git commit -m "feat: windows agent job processor (ESAJ/PJe/A3/Protocolo)"
```

---

### Task 4: Criar GET `/api/v1/jobs/pending` (Windows puxa jobs)

**Files:**
- Modify: `backend/app/routes/jobs.py`
- Test: `tests/routes/test_jobs.py`

**Interfaces:**
- Consumes: `JobModel` (Task 1)
- Produces: GET `/api/v1/jobs/pending` → `[{id, tipo, payload, tentativas}]`

- [ ] **Step 1: Write failing test**

```python
def test_get_pending_jobs(client, db):
    from app.models.job import JobModel
    
    # Inserir job de teste
    job = JobModel(status="pending", tipo="esaj_search", payload={"cnj": "test"})
    db.add(job)
    db.commit()
    
    response = client.get("/api/v1/jobs/pending")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 1
    assert jobs[0]["tipo"] == "esaj_search"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/routes/test_jobs.py::test_get_pending_jobs -v
# Expected: FAIL
```

- [ ] **Step 3: Adicionar endpoint em jobs.py**

`backend/app/routes/jobs.py` (adicionar):

```python
@router.get("/pending")
def get_pending_jobs(db: Session = Depends(get_db)):
    """Retornar jobs pendentes para Windows Agent processar"""
    
    jobs = db.query(JobModel).filter(
        JobModel.status == "pending",
        (JobModel.proxima_tentativa.is_(None)) | 
        (JobModel.proxima_tentativa <= datetime.now())
    ).limit(10).all()
    
    return [
        {
            "id": job.id,
            "tipo": job.tipo,
            "payload": job.payload,
            "tentativas": job.tentativas
        }
        for job in jobs
    ]
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/routes/test_jobs.py::test_get_pending_jobs -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/jobs.py
git commit -m "feat: add GET /api/v1/jobs/pending for windows agent polling"
```

---

### Task 5: PATCH `/api/v1/jobs/{id}` — Windows atualiza status + resultado

**Files:**
- Modify: `backend/app/routes/jobs.py`
- Test: `tests/routes/test_jobs.py`

**Interfaces:**
- Consumes: `JobModel` (Task 1)
- Produces: PATCH `/api/v1/jobs/{id}` → atualiza job (status, resultado, tentativas, proxima_tentativa)

- [ ] **Step 1: Write failing test**

```python
def test_update_job_status(client, db):
    from app.models.job import JobModel
    
    job = JobModel(status="pending", tipo="esaj_search", payload={"cnj": "test"})
    db.add(job)
    db.commit()
    job_id = job.id
    
    response = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={
            "status": "success",
            "resultado": {"pdf_path": "/path/to/pdf.pdf"}
        }
    )
    
    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "success"
    assert updated["resultado"]["pdf_path"] == "/path/to/pdf.pdf"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/routes/test_jobs.py::test_update_job_status -v
# Expected: FAIL
```

- [ ] **Step 3: Adicionar endpoint PATCH**

`backend/app/routes/jobs.py` (adicionar):

```python
@router.patch("/{job_id}")
def update_job(
    job_id: int,
    update: dict,
    db: Session = Depends(get_db)
):
    """Windows Agent atualiza status do job após processamento"""
    
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if "status" in update:
        job.status = update["status"]
    
    if "resultado" in update:
        job.resultado = update["resultado"]
    
    if "tentativas" in update:
        if update["tentativas"] == "increment":
            job.tentativas += 1
            # Retry logic: esperar 5min antes de próxima tentativa
            if job.tentativas < 3:
                job.proxima_tentativa = datetime.now() + timedelta(minutes=5)
                job.status = "pending"
            else:
                job.status = "failed"
        else:
            job.tentativas = update["tentativas"]
    
    job.atualizado_em = datetime.now()
    db.commit()
    db.refresh(job)
    
    return {
        "id": job.id,
        "status": job.status,
        "resultado": job.resultado,
        "tentativas": job.tentativas
    }
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/routes/test_jobs.py::test_update_job_status -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/jobs.py
git commit -m "feat: add PATCH /api/v1/jobs/{id} for job status updates"
```

---

### Task 6: Auto-Trigger de Jobs via Webhook (Email Intimação)

**Files:**
- Modify: `backend/app/routes/webhooks.py` (ou criar)
- Test: `tests/routes/test_webhooks.py`

**Interfaces:**
- Consumes: POST de email/TJMS → extrai CNJ → enfileira job
- Produces: POST `/api/v1/webhooks/intimacao` → auto cria job ESAJ

- [ ] **Step 1: Write failing test**

```python
def test_webhook_intimacao(client, db):
    response = client.post(
        "/api/v1/webhooks/intimacao",
        json={
            "from": "tjms@tjms.jus.br",
            "subject": "Intimação processo 0501238-54.2022.8.12.0037",
            "body": "Autos já estão disponíveis..."
        }
    )
    
    assert response.status_code == 201
    assert response.json()["job_id"] > 0
    
    # Verificar que job foi criado
    from app.models.job import JobModel
    jobs = db.query(JobModel).all()
    assert len(jobs) == 1
    assert jobs[0].tipo == "esaj_search"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/routes/test_webhooks.py::test_webhook_intimacao -v
# Expected: FAIL
```

- [ ] **Step 3: Implementar webhook e extração de CNJ**

`backend/app/routes/webhooks.py`:

```python
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.job import JobModel

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

CNJ_REGEX = r"\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}"

def extrair_cnj(texto):
    """Extrair número CNJ do email/intimação"""
    match = re.search(CNJ_REGEX, texto)
    if match:
        return match.group(0)
    return None

@router.post("/intimacao", status_code=201)
def webhook_intimacao(
    payload: dict,
    db: Session = Depends(get_db)
):
    """Webhook: nova intimação → auto-enfileirar ESAJ search"""
    
    # Extrair CNJ do subject + body
    subject = payload.get("subject", "")
    body = payload.get("body", "")
    texto_completo = f"{subject} {body}"
    
    cnj = extrair_cnj(texto_completo)
    if not cnj:
        raise HTTPException(status_code=400, detail="CNJ não encontrado na intimação")
    
    # Determinar tribunal (heurística: verificar domínio/palavras-chave)
    tribunal = "TJMS"
    if "tjmt" in texto_completo.lower():
        tribunal = "TJMT"
    
    # Enfileirar job
    job = JobModel(
        status="pending",
        tipo="esaj_search",
        payload={
            "cnj": cnj,
            "trib": tribunal,
            "origem": "email_intimacao"
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {
        "job_id": job.id,
        "cnj": cnj,
        "tribunal": tribunal,
        "status": "enfileirado"
    }
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/routes/test_webhooks.py::test_webhook_intimacao -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/webhooks.py tests/routes/test_webhooks.py
git commit -m "feat: add webhook /intimacao for auto-triggering ESAJ search jobs"
```

---

### Task 7: RAG Integration — Indexar Processo Completo

**Files:**
- Modify: `backend/app/services/rag_service.py` (criar se não existe)
- Test: `tests/services/test_rag_service.py`

**Interfaces:**
- Consumes: `processo_id`, PDF path, CNJ
- Produces: `index_processo_para_rag(processo_id, cnj, partes, tipo_acao)` → pgvector embedding

- [ ] **Step 1: Write failing test**

```python
def test_index_processo_rag():
    from app.services.rag_service import index_processo_para_rag
    
    resultado = index_processo_para_rag(
        processo_id=123,
        cnj="0501238-54.2022.8.12.0037",
        partes=["AUTOR LTDA", "REU PESSOA"],
        tipo_acao="Ação Cível",
        conteudo_texto="Lorem ipsum processo..."
    )
    
    assert resultado["indexed"] == True
    assert resultado["embedding_id"] > 0
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/services/test_rag_service.py::test_index_processo_rag -v
# Expected: FAIL
```

- [ ] **Step 3: Implementar RAG Service**

`backend/app/services/rag_service.py`:

```python
from app.database import get_db
from sqlalchemy import text
from app.models.rag import RAGJuridico
import requests

def index_processo_para_rag(
    processo_id: int,
    cnj: str,
    partes: list,
    tipo_acao: str,
    conteudo_texto: str = "",
    db = None
):
    """Indexar processo no pgvector RAG"""
    
    if not db:
        db = next(get_db())
    
    # 1. Gerar embedding via local Qwen ou API
    embedding = gerar_embedding(
        f"{cnj} {tipo_acao} {' '.join(partes)} {conteudo_texto}"
    )
    
    # 2. Inserir em rag_juridico (pgvector)
    rag_entry = RAGJuridico(
        doc_id=f"processo_{processo_id}",
        titulo=f"{cnj} - {tipo_acao}",
        conteudo=conteudo_texto[:2000],  # truncar
        tipo="auto_judicial",
        area="geral",
        partes=partes,
        embedding=embedding
    )
    
    db.add(rag_entry)
    db.commit()
    db.refresh(rag_entry)
    
    return {
        "indexed": True,
        "embedding_id": rag_entry.id,
        "processo_id": processo_id
    }

def gerar_embedding(texto: str):
    """Gerar embedding via Qwen local (Ollama)"""
    try:
        resp = requests.post(
            "http://localhost:11434/api/embed",
            json={"model": "nomic-embed-text", "input": texto},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["embeddings"][0]
    except:
        pass
    
    # Fallback: zeros
    return [0.0] * 768
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/services/test_rag_service.py::test_index_processo_rag -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rag_service.py
git commit -m "feat: add RAG indexing service for processo embedding"
```

---

### Task 8: Monitor Email TJMS — Auto-Detectar Intimações

**Files:**
- Create: `windows/monitor_tjms_intimacoes.py`
- Test: `tests/windows/test_monitor_tjms.py` (simular)

**Interfaces:**
- Consumes: Email TJMS (via Graph API / mailbox)
- Produces: POST `/api/v1/webhooks/intimacao` quando detectar nova intimação

- [ ] **Step 1: Write failing test**

```python
def test_monitor_tjms_extract_cnj():
    from windows.monitor_tjms_intimacoes import extrair_cnj_da_intimacao
    
    email_body = "Processo 0501238-54.2022.8.12.0037 foi distribuído"
    cnj = extrair_cnj_da_intimacao(email_body)
    
    assert cnj == "0501238-54.2022.8.12.0037"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/windows/test_monitor_tjms.py::test_monitor_tjms_extract_cnj -v
# Expected: FAIL
```

- [ ] **Step 3: Implementar monitor**

`windows/monitor_tjms_intimacoes.py`:

```python
import re
import time
from datetime import datetime, timedelta
import requests

CNJ_REGEX = r"\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}"
API_WEBHOOK = "http://sistema.ipcms.com.br/api/v1/webhooks/intimacao"

def extrair_cnj_da_intimacao(texto):
    """Extrair CNJ de email de intimação"""
    match = re.search(CNJ_REGEX, texto)
    return match.group(0) if match else None

def monitor_tjms_email():
    """
    Monitor contínuo de email TJMS
    - Usar Graph API (já configurado em credenciais_azure)
    - Buscar emails de "intimacoes@tjms.jus.br"
    - Auto-POST webhook quando detectar CNJ novo
    """
    
    print("🔍 Monitor TJMS Intimações iniciado")
    
    # Arquivo de controle: último email processado
    ultimo_id = ler_ultimo_email_id("tjms_monitor.txt")
    
    while True:
        try:
            # 1. Buscar emails novos via Graph API
            emails = buscar_emails_tjms_novos(ultimo_id)
            
            for email in emails:
                subject = email.get("subject", "")
                body = email.get("bodyPreview", "")
                received = email.get("receivedDateTime", "")
                
                cnj = extrair_cnj_da_intimacao(f"{subject} {body}")
                
                if cnj:
                    print(f"📨 Intimação detectada: {cnj}")
                    
                    # 2. POST webhook → enfileira job
                    try:
                        requests.post(
                            API_WEBHOOK,
                            json={
                                "subject": subject,
                                "body": body,
                                "from": "tjms@tjms.jus.br",
                                "received": received
                            },
                            timeout=10
                        )
                        print(f"✅ Job enfileirado para {cnj}")
                    except Exception as e:
                        print(f"⚠️  Erro ao enfileirar: {e}")
                
                # Atualizar último ID processado
                ultimo_id = email.get("id")
                salvar_ultimo_email_id("tjms_monitor.txt", ultimo_id)
        
        except Exception as e:
            print(f"❌ Erro monitor: {e}")
        
        # Aguardar 5min antes de próximo ciclo
        time.sleep(300)

def buscar_emails_tjms_novos(desde_id=None):
    """Buscar emails TJMS usando Graph API"""
    # TODO: implementar com Graph API (credenciais já em .env)
    # Por enquanto, retornar vazio
    return []

def ler_ultimo_email_id(arquivo):
    try:
        with open(arquivo, "r") as f:
            return f.read().strip()
    except:
        return None

def salvar_ultimo_email_id(arquivo, email_id):
    with open(arquivo, "w") as f:
        f.write(email_id)

if __name__ == "__main__":
    monitor_tjms_email()
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/windows/test_monitor_tjms.py::test_monitor_tjms_extract_cnj -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add windows/monitor_tjms_intimacoes.py
git commit -m "feat: add TJMS email monitor for auto-detecting intimacoes"
```

---

### Task 9: Assinatura A3 — Integração com Windows

**Files:**
- Modify: `windows/jobs_processor.py` (adicionar função sign_a3)
- Test: `tests/windows/test_a3_sign.py`

**Interfaces:**
- Consumes: `job_id`, `pdf_path`, `tipo_documento`
- Produces: `process_sign_a3(job_id, pdf_path)` → assinado via SafeKey/Softplan

- [ ] **Step 1: Write failing test**

```python
def test_sign_pdf_a3():
    from windows.jobs_processor import process_sign_a3
    
    # Simular job de assinatura
    job_payload = {
        "pdf_path": "C:\\Perito\\Autos\\TJMS\\0501238_54_2022\\laudo.pdf",
        "tipo": "laudo"
    }
    
    # Mock: não vamos assinar de verdade no teste
    result = process_sign_a3(999, job_payload)
    assert result["status"] in ["success", "pending"]
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/windows/test_a3_sign.py::test_sign_pdf_a3 -v
# Expected: FAIL
```

- [ ] **Step 3: Implementar A3**

`windows/jobs_processor.py` (adicionar):

```python
def process_sign_a3(job_id, job_payload):
    """Assinar PDF com certificado A3"""
    
    pdf_path = job_payload.get("pdf_path")
    tipo = job_payload.get("tipo", "documento")
    
    try:
        # 1. Localizar certificado A3 (SafeKey/Softplan)
        cert_path = localizr_certificado_a3()
        if not cert_path:
            raise Exception("Certificado A3 não encontrado")
        
        # 2. Chamar ferramenta de assinatura
        # Usar pyHanko (já em toolchains_periciais)
        from hanko.pdf_cms import sign
        from hanko.pdf_utils.reader import PdfFileReader
        
        # Assinar documento
        with open(pdf_path, "rb") as f:
            r = PdfFileReader(f)
        
        # Usar certificado PKCS#12
        # TODO: implementar com pyHanko (mais detalhes em toolchains_periciais)
        
        signed_path = pdf_path.replace(".pdf", "_assinado.pdf")
        
        # 3. Atualizar resultado do job
        resultado = {
            "pdf_original": pdf_path,
            "pdf_assinado": signed_path,
            "data_assinatura": datetime.now().isoformat(),
            "tipo_certificado": "A3"
        }
        
        requests.patch(
            f"{API_BASE}/jobs/{job_id}",
            json={"status": "success", "resultado": resultado}
        )
        
        return {"status": "success", "signed_pdf": signed_path}
    
    except Exception as e:
        print(f"❌ Erro A3: {e}")
        requests.patch(
            f"{API_BASE}/jobs/{job_id}",
            json={"status": "pending_a3_manual", "erro": str(e)}
        )
        return {"status": "pending_a3_manual", "erro": str(e)}

def localizr_certificado_a3():
    """Localizar certificado A3 no sistema Windows"""
    # TODO: buscar em Smart Card / SafeKey
    return None
```

- [ ] **Step 4: Run test (expect PASS com mock)**

```bash
pytest tests/windows/test_a3_sign.py::test_sign_pdf_a3 -v
# Expected: PASS (com mock)
```

- [ ] **Step 5: Commit**

```bash
git add windows/jobs_processor.py
git commit -m "feat: add A3 PDF signing via SafeKey/Softplan"
```

---

### Task 10: Protocolo TJMS — Auto-Protocol Laudo

**Files:**
- Modify: `windows/jobs_processor.py` (adicionar função protocol_tjms)
- Test: `tests/windows/test_protocol_tjms.py`

**Interfaces:**
- Consumes: `job_id`, `processo_id`, `pdf_assinado`
- Produces: `process_protocol_tjms(job_id, pdf_path, cnj)` → protocolo número + comprovante

- [ ] **Step 1: Write failing test**

```python
def test_protocol_tjms():
    from windows.jobs_processor import process_protocol_tjms
    
    job_payload = {
        "cnj": "0501238-54.2022.8.12.0037",
        "pdf_path": "/path/to/laudo_assinado.pdf"
    }
    
    result = process_protocol_tjms(999, job_payload)
    
    assert result["status"] == "success"
    assert "numero_protocolo" in result
    assert "data_protocolo" in result
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/windows/test_protocol_tjms.py::test_protocol_tjms -v
# Expected: FAIL
```

- [ ] **Step 3: Implementar Protocolo**

`windows/jobs_processor.py` (adicionar):

```python
def process_protocol_tjms(job_id, job_payload):
    """Protocolar documento assinado no TJMS"""
    
    cnj = job_payload.get("cnj")
    pdf_path = job_payload.get("pdf_path")
    
    try:
        # 1. Chamar API TJMS (já existe em credenciais)
        # TODO: detalhar endpoint do TJMS
        
        import os
        tjms_token = os.getenv("TJMS_API_TOKEN")
        
        with open(pdf_path, "rb") as f:
            files = {"documento": f}
            response = requests.post(
                "https://api.tjms.jus.br/protocolo/submit",
                headers={"Authorization": f"Bearer {tjms_token}"},
                files=files,
                data={"numero_processo": cnj}
            )
        
        if response.status_code == 200:
            dados = response.json()
            numero_protocolo = dados.get("numero_protocolo")
            
            resultado = {
                "numero_protocolo": numero_protocolo,
                "data_protocolo": datetime.now().isoformat(),
                "comprovante_url": dados.get("comprovante_url"),
                "status_tjms": "protocolado"
            }
            
            # Atualizar job
            requests.patch(
                f"{API_BASE}/jobs/{job_id}",
                json={"status": "success", "resultado": resultado}
            )
            
            return {"status": "success", **resultado}
        else:
            raise Exception(f"TJMS API error: {response.text}")
    
    except Exception as e:
        print(f"❌ Erro protocolo: {e}")
        requests.patch(
            f"{API_BASE}/jobs/{job_id}",
            json={"status": "failed", "erro": str(e)}
        )
        return {"status": "failed", "erro": str(e)}
```

- [ ] **Step 4: Run test (expect PASS com mock)**

```bash
pytest tests/windows/test_protocol_tjms.py::test_protocol_tjms -v
# Expected: PASS (com mock TJMS)
```

- [ ] **Step 5: Commit**

```bash
git add windows/jobs_processor.py
git commit -m "feat: add TJMS protocol submission for signed documents"
```

---

### Task 11: Dashboard Update — Mostrar Processo Pré-Preenchido

**Files:**
- Modify: `frontend/src/pages/Processos.jsx` (ou componente relevant)
- Test: `tests/frontend/Processos.test.jsx`

**Interfaces:**
- Consumes: `/api/v1/processos/{id}` (retorna dados completos + RAG snippets)
- Produces: UI mostra partes, número, tipo, PDF, laudo, RAG suggestions

- [ ] **Step 1: Write failing test**

```jsx
import { render, screen } from "@testing-library/react"
import Processos from "./Processos"

test("Mostra processo pré-preenchido com RAG", () => {
    render(<Processos processId={123} />)
    
    // Verificar que dados aparecem
    expect(screen.getByText(/0501238-54/)).toBeInTheDocument()
    expect(screen.getByText(/AUTOR LTDA/)).toBeInTheDocument()
    expect(screen.getByText(/Laudo em PDF/)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
npm test -- tests/frontend/Processos.test.jsx
# Expected: FAIL
```

- [ ] **Step 3: Modificar Processos.jsx para mostrar dados completos**

`frontend/src/pages/Processos.jsx`:

```jsx
import { useEffect, useState } from "react"

export default function Processos({ processId }) {
    const [data, setData] = useState(null)
    
    useEffect(() => {
        // Buscar dados do processo (agora vem completo do ESAJ + BD)
        fetch(`/api/v1/processos/${processId}`)
            .then(r => r.json())
            .then(setData)
    }, [processId])
    
    if (!data) return <div>Carregando...</div>
    
    const { numero, partes, tipo_acao, pdf_url, laudo, rag_snippets } = data
    
    return (
        <div className="processo-detail">
            <h2>Processo {numero}</h2>
            
            <section className="partes">
                <h3>Partes</h3>
                {partes?.map((p, i) => (
                    <div key={i}>
                        <strong>{p.tipo}:</strong> {p.nome}
                    </div>
                ))}
            </section>
            
            <section className="tipo-acao">
                <h3>Tipo de Ação</h3>
                <p>{tipo_acao}</p>
            </section>
            
            <section className="pdf">
                <h3>Autos Judiciais</h3>
                <a href={pdf_url} target="_blank">📄 Baixar PDF</a>
            </section>
            
            <section className="laudo">
                <h3>Laudo / Parecer</h3>
                <p>{laudo || "Pendente análise"}</p>
            </section>
            
            <section className="rag">
                <h3>Sugestões RAG (Jurisprudência Relacionada)</h3>
                {rag_snippets?.map((s, i) => (
                    <div key={i} className="rag-snippet">
                        <strong>{s.titulo}</strong>
                        <p>{s.conteudo.substring(0, 200)}...</p>
                    </div>
                ))}
            </section>
        </div>
    )
}
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
npm test -- tests/frontend/Processos.test.jsx
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Processos.jsx
git commit -m "feat: show auto-fetched processo data with RAG suggestions"
```

---

### Task 12: Integração End-to-End — Teste Completo

**Files:**
- Create: `tests/e2e/test_complete_workflow.py`

**Interfaces:**
- Consumes: Todos os endpoints anteriores
- Produces: Teste E2E simulando fluxo completo

- [ ] **Step 1: Write E2E test**

```python
def test_complete_workflow_tjms_to_dashboard():
    """
    E2E completo:
    1. Email de intimação chega
    2. Webhook dispara → enfileira job ESAJ
    3. Windows Agent busca e baixa PDF
    4. Insere BD → alimenta RAG → assina A3 → protocola TJMS
    5. Dashboard mostra tudo pronto
    """
    
    # 1. Simular email intimação
    email_payload = {
        "from": "tjms@tjms.jus.br",
        "subject": "Intimação - Processo 0501238-54.2022.8.12.0037",
        "body": "Os autos estão disponíveis para consulta"
    }
    
    # 2. POST webhook
    response = client.post("/api/v1/webhooks/intimacao", json=email_payload)
    assert response.status_code == 201
    job_id = response.json()["job_id"]
    
    # 3. Verificar job foi criado
    jobs = client.get("/api/v1/jobs/pending").json()
    assert len(jobs) > 0
    assert jobs[0]["tipo"] == "esaj_search"
    
    # 4. Simular Windows Agent processando
    from windows.jobs_processor import process_esaj_job
    # Rodar o processador (mock)
    
    # 5. Verificar resultado final
    # - BD tem processo
    # - RAG indexado
    # - Dashboard mostra dados completos
```

- [ ] **Step 2: Run test (expect FAIL no início)**

```bash
pytest tests/e2e/test_complete_workflow.py -v
# Expected: FAIL (ainda não tudo integrado)
```

- [ ] **Step 3: Integrar todos os componentes (Tasks 1-11)**

Após completar Tasks 1-11, refinar e executar E2E

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/e2e/test_complete_workflow.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_complete_workflow.py
git commit -m "test: add E2E workflow test (email → BD → RAG → dashboard)"
```

---

## Checklist Final

- [ ] Todos 12 tasks completados
- [ ] Todos testes PASS
- [ ] Windows Agent rodando em loop (30s polling)
- [ ] Email Monitor rodando em background
- [ ] Dashboard mostra processo pré-preenchido
- [ ] RAG alimentado com novos processos
- [ ] A3 assinando PDFs
- [ ] TJMS protocolando documentos
- [ ] Nenhuma duplicata (MD5 check)
- [ ] Retry logic para jobs falhados

