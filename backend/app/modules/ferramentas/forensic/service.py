"""Service layer for forensic analysis and laudo operations."""

import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models import LaudoForense, ClienteForense, Job


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ (formato básico)."""
    cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
    return len(cnpj) == 14 and cnpj.isdigit()


class ForensicService:
    """Service for forensic analysis and laudo operations."""

    async def criar_laudo_forense(
        self,
        arquivo: UploadFile,
        cliente_nome: str,
        cliente_cnpj: str,
        cliente_email: str,
        origem_midia: str = "Outro",
        descricao: str = "",
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Cria novo laudo forense e enfileira análise.

        Args:
            arquivo: Upload file (vídeo/áudio/imagem)
            cliente_nome: Nome do cliente
            cliente_cnpj: CNPJ do cliente
            cliente_email: Email do cliente
            origem_midia: Origem da mídia (WhatsApp, Email, Pen Drive, Outro)
            descricao: Descrição opcional
            db: Database session

        Returns:
            Dict with numero_laudo, status, job_id, and cliente info

        Raises:
            HTTPException: If CNPJ is invalid or file exceeds size limit
        """
        # Validar CNPJ
        if not validar_cnpj(cliente_cnpj):
            raise HTTPException(status_code=400, detail="CNPJ inválido")

        # Limpar CNPJ
        cliente_cnpj_clean = cliente_cnpj.replace('.', '').replace('/', '').replace('-', '')

        # Salvar arquivo temporariamente
        conteudo = await arquivo.read()
        if len(conteudo) > 500 * 1024 * 1024:  # 500MB max
            raise HTTPException(status_code=413, detail="Arquivo > 500MB")

        # Criar hash do arquivo
        hash_arquivo = hashlib.md5(conteudo).hexdigest()

        # Salvar em temp
        suffix = Path(arquivo.filename).suffix if arquivo.filename else '.bin'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            tmp.write(conteudo)

        # Criar/buscar cliente
        cliente = db.query(ClienteForense).filter(
            ClienteForense.cnpj == cliente_cnpj_clean
        ).first()
        if not cliente:
            cliente = ClienteForense(
                nome=cliente_nome,
                cnpj=cliente_cnpj_clean,
                email=cliente_email
            )
            db.add(cliente)
            db.commit()
            db.refresh(cliente)

        # Gerar número do laudo
        last_laudo = db.query(LaudoForense).order_by(LaudoForense.id.desc()).first()
        laudo_numero = f"LF-{datetime.now().year}-{(last_laudo.id if last_laudo else 0) + 1:05d}"

        # Criar LaudoForense (status='processando')
        laudo = LaudoForense(
            numero_laudo=laudo_numero,
            cliente_id=cliente.id,
            arquivo_hash=hash_arquivo,
            arquivo_nome=arquivo.filename or "arquivo",
            arquivo_tamanho_mb=len(conteudo) / 1024 / 1024,
            arquivo_tipo=arquivo.content_type or "unknown",
            origem_midia=origem_midia,
            descricao=descricao,
            status='processando',
        )
        db.add(laudo)
        db.commit()
        db.refresh(laudo)

        # Enfileirar job de análise
        job = Job(
            tipo='forensic-analyze',
            status='na_fila',
            parametros={
                'laudo_id': laudo.id,
                'arquivo_path': tmp_path,
                'numero_laudo': laudo_numero,
            }
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        return {
            "numero_laudo": laudo_numero,
            "status": "processando",
            "job_id": str(job.id),
            "cliente": {
                "nome": cliente.nome,
                "cnpj": cliente.cnpj,
                "email": cliente.email,
            }
        }

    async def obter_laudo(
        self,
        numero_laudo: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Recupera laudo forense completo.

        Args:
            numero_laudo: Número do laudo
            db: Database session

        Returns:
            Dict with complete laudo information

        Raises:
            HTTPException: If laudo not found
        """
        laudo = db.query(LaudoForense).filter(
            LaudoForense.numero_laudo == numero_laudo
        ).first()

        if not laudo:
            raise HTTPException(status_code=404, detail="Laudo não encontrado")

        # Formatar resposta
        return {
            "numero_laudo": laudo.numero_laudo,
            "cliente": {
                "nome": laudo.cliente.nome if laudo.cliente else None,
                "cnpj": laudo.cliente.cnpj if laudo.cliente else None,
                "email": laudo.cliente.email if laudo.cliente else None,
            },
            "arquivo_hash": laudo.arquivo_hash,
            "arquivo_nome": laudo.arquivo_nome,
            "arquivo_tamanho_mb": laudo.arquivo_tamanho_mb,
            "veredicto": laudo.veredicto or "PROCESSANDO",
            "authenticity_score": laudo.authenticity_score,
            "consensus": laudo.consensus,
            "status": laudo.status or "processando",
            "pdf_url": f"/api/v1/media/forensic-laudo/{numero_laudo}/pdf" if laudo.pdf_path else None,
            "created_at": laudo.created_at.isoformat() if laudo.created_at else None,
            "resultados_apis": laudo.resultados_apis or [],
        }

    async def download_pdf_laudo(
        self,
        numero_laudo: str,
        db: Session,
    ):
        """
        Download do PDF do laudo forense.

        Args:
            numero_laudo: Número do laudo
            db: Database session

        Returns:
            FileResponse with PDF

        Raises:
            HTTPException: If PDF not found
        """
        laudo = db.query(LaudoForense).filter(
            LaudoForense.numero_laudo == numero_laudo
        ).first()

        if not laudo or not laudo.pdf_path:
            raise HTTPException(status_code=404, detail="PDF não disponível")

        pdf_path = Path(laudo.pdf_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado")

        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"{numero_laudo}.pdf"
        )

    async def listar_laudos(
        self,
        skip: int = 0,
        limit: int = 20,
        status_filtro: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Lista laudos forenses.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status_filtro: Filter by status
            db: Database session

        Returns:
            Dict with total count and list of laudos
        """
        query = db.query(LaudoForense)

        if status_filtro:
            query = query.filter(LaudoForense.status == status_filtro)

        total = query.count()
        laudos = query.order_by(LaudoForense.id.desc()).offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [
                {
                    "numero_laudo": l.numero_laudo,
                    "cliente": l.cliente.nome if l.cliente else None,
                    "status": l.status or "processando",
                    "veredicto": l.veredicto,
                    "authenticity_score": l.authenticity_score,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in laudos
            ]
        }
