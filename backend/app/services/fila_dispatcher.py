from app.models.fila_jobs import FilaJob, JobStatus
from app.database import SessionLocal
from sqlalchemy.orm import Session

def enfileirar_processamento(fila_id: int, oficio_path: str, db: Session):
    """Enfileira job de processamento PDF → Qwen"""
    
    # Job 1: Extrair PDF
    job_pdf = FilaJob(
        tipo="processar_pdf",
        fila_id=fila_id,
        payload={"oficio_path": oficio_path},
        status=JobStatus.PENDENTE
    )
    
    # Job 2: Analisar com Qwen (dependente do 1)
    job_qwen = FilaJob(
        tipo="analisar_qwen",
        fila_id=fila_id,
        payload={"fila_id": fila_id},
        status=JobStatus.PENDENTE
    )
    
    db.add(job_pdf)
    db.add(job_qwen)
    db.commit()
    
    return {"job_pdf_id": job_pdf.id, "job_qwen_id": job_qwen.id}
