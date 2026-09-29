from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.fila_intimacoes import FilaIntimacao
from app.jobs.processar_oficio_pdf import extrair_texto_pdf
from app.jobs.analisar_intimacao_qwen import analisar_intimacao
import os
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/ferramentas/e2e", tags=["e2e"])

@router.post("/processar-oficio")
async def processar_oficio_e2e(
    laudo_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """E2E: Upload → Extrair PDF → Analisar Qwen → Salvar Fila"""
    
    # 1. Salvar arquivo
    upload_path = f"/tmp/{file.filename}"
    with open(upload_path, "wb") as f:
        f.write(await file.read())
    
    # 2. Extrair PDF
    pdf_resultado = extrair_texto_pdf(upload_path)
    if pdf_resultado["erro"]:
        return {"erro": pdf_resultado["erro"]}
    
    # 3. Analisar Qwen
    qwen_resultado = analisar_intimacao(pdf_resultado["texto"], laudo_id)
    
    # 4. Criar fila
    fila_item = FilaIntimacao(
        laudo_id=laudo_id,
        oficio_path=upload_path,
        criado_por=1
    )
    db.add(fila_item)
    db.commit()
    
    # Limpar temp
    os.remove(upload_path)
    
    return {
        "fila_id": fila_item.id,
        "pdf_qualidade": pdf_resultado["qualidade"],
        "analise": qwen_resultado
    }
