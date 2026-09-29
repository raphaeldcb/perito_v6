"""
Analysis repository for CRUD operations.

Handles persistence of analysis records to database.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.modules.ia.models import Analysis, RAGDocument
from app.models import User
from app.shared.exceptions import ResourceNotFoundException


class AnalysisRepository:
    """Repository for Analysis model persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_analysis(
        self,
        user_id: int,
        input_text: str,
        analysis_result: str,
        model: str = "perito-qwen",
        provider: str = "ollama",
        processo_id: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost_usd: float = 0.0,
        rag_context: Optional[dict] = None,
        status: str = "completed",
        error_detail: Optional[str] = None,
    ) -> Analysis:
        """Create a new analysis record."""
        analysis = Analysis(
            user_id=user_id,
            input_text=input_text,
            analysis_result=analysis_result,
            model=model,
            provider=provider,
            processo_id=processo_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            rag_context=rag_context,
            status=status,
            error_detail=error_detail,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_analysis_by_id(self, analysis_id: int) -> Optional[Analysis]:
        """Get analysis by ID."""
        return self.db.query(Analysis).filter(Analysis.id == analysis_id).first()

    def get_user_analyses(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Analysis], int]:
        """Get all analyses for a user with pagination."""
        query = self.db.query(Analysis).filter(Analysis.user_id == user_id)
        total = query.count()
        analyses = query.order_by(desc(Analysis.created_at)).limit(limit).offset(offset).all()
        return analyses, total

    def get_processo_analyses(
        self,
        processo_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Analysis], int]:
        """Get all analyses for a specific process."""
        query = self.db.query(Analysis).filter(Analysis.processo_id == processo_id)
        total = query.count()
        analyses = query.order_by(desc(Analysis.created_at)).limit(limit).offset(offset).all()
        return analyses, total

    def update_analysis(
        self,
        analysis_id: int,
        **kwargs,
    ) -> Analysis:
        """Update an analysis record."""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise ResourceNotFoundException(
                f"Analysis {analysis_id} not found",
                error_code="ANALYSIS_NOT_FOUND",
            )
        for key, value in kwargs.items():
            if hasattr(analysis, key):
                setattr(analysis, key, value)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete an analysis record."""
        analysis = self.get_analysis_by_id(analysis_id)
        if not analysis:
            raise ResourceNotFoundException(
                f"Analysis {analysis_id} not found",
                error_code="ANALYSIS_NOT_FOUND",
            )
        self.db.delete(analysis)
        self.db.commit()
        return True


class RAGDocumentRepository:
    """Repository for RAGDocument model persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_document(
        self,
        source_file: str,
        content: str,
        source_url: Optional[str] = None,
        document_type: str = "laudo",
        chunk_index: int = 0,
        title: Optional[str] = None,
        area: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> RAGDocument:
        """Create a new RAG document chunk."""
        doc = RAGDocument(
            source_file=source_file,
            content=content,
            source_url=source_url,
            document_type=document_type,
            chunk_index=chunk_index,
            title=title,
            area=area,
            tags=tags or [],
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document_by_id(self, doc_id: int) -> Optional[RAGDocument]:
        """Get document chunk by ID."""
        return self.db.query(RAGDocument).filter(RAGDocument.id == doc_id).first()

    def get_documents_by_area(
        self,
        area: str,
        limit: int = 50,
    ) -> List[RAGDocument]:
        """Get document chunks by expertise area."""
        return (
            self.db.query(RAGDocument)
            .filter(RAGDocument.area == area, RAGDocument.is_indexed == 1)
            .limit(limit)
            .all()
        )

    def get_indexed_documents(
        self,
        limit: int = 100,
    ) -> List[RAGDocument]:
        """Get all indexed documents ready for RAG search."""
        return (
            self.db.query(RAGDocument)
            .filter(RAGDocument.is_indexed == 1, RAGDocument.is_embedded == 1)
            .limit(limit)
            .all()
        )

    def update_document(
        self,
        doc_id: int,
        **kwargs,
    ) -> RAGDocument:
        """Update a document chunk."""
        doc = self.get_document_by_id(doc_id)
        if not doc:
            raise ResourceNotFoundException(
                f"RAG document {doc_id} not found",
                error_code="RAG_DOCUMENT_NOT_FOUND",
            )
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document chunk."""
        doc = self.get_document_by_id(doc_id)
        if not doc:
            raise ResourceNotFoundException(
                f"RAG document {doc_id} not found",
                error_code="RAG_DOCUMENT_NOT_FOUND",
            )
        self.db.delete(doc)
        self.db.commit()
        return True
