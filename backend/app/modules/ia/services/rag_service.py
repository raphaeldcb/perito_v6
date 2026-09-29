"""
RAG service for semantic search and context retrieval.

Uses pgvector for similarity search (wave 2).
Wave 1: Simple vector storage in JSON for MVP.
"""

import logging
import os
from typing import Optional, List, Dict, Any
import json
from sqlalchemy.orm import Session

from app.modules.ia.models import RAGDocument
from app.modules.ia.repositories import RAGDocumentRepository
from app.shared.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)

# Embedding model (local, via Ollama)
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


class RAGService:
    """
    RAG service for semantic search.

    Wave 1: Simple cosine similarity on stored embeddings.
    Wave 2: Use pgvector for efficient similarity search.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = RAGDocumentRepository(db)
        self.embedding_model = EMBEDDING_MODEL

    async def search(
        self,
        query: str,
        top_k: int = 5,
        area: Optional[str] = None,
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            area: Filter by expertise area (optional)
            threshold: Minimum similarity score (0-1)

        Returns:
            List of RAG results sorted by relevance_score (descending)
        """
        # Get query embedding
        try:
            query_embedding = await self._get_embedding(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise ExternalServiceException(
                detail="Failed to generate query embedding",
                error_code="EMBEDDING_ERROR",
            ) from e

        # Get indexed documents
        documents = self.repo.get_indexed_documents(limit=100)
        if not documents:
            logger.warning("No indexed RAG documents found")
            return []

        # Calculate similarity scores
        results = []
        for doc in documents:
            # Filter by area if specified
            if area and doc.area != area:
                continue

            # Skip if embedding missing
            if not doc.embedding or not isinstance(doc.embedding, (dict, list)):
                continue

            # Calculate cosine similarity
            try:
                doc_embedding = (
                    doc.embedding if isinstance(doc.embedding, list) else
                    json.loads(json.dumps(doc.embedding))
                )
                score = self._cosine_similarity(query_embedding, doc_embedding)

                if score >= threshold:
                    results.append({
                        "id": doc.id,
                        "source_file": doc.source_file,
                        "content": doc.content,
                        "area": doc.area,
                        "relevance_score": score,
                        "tags": doc.tags or [],
                    })
            except Exception as e:
                logger.warning(f"Error scoring document {doc.id}: {e}")
                continue

        # Sort by relevance and return top-k
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using nomic-embed-text (via Ollama).

        Returns:
            768-dimensional vector
        """
        import httpx

        payload = {
            "model": self.embedding_model,
            "prompt": text,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/embeddings",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                embedding = data.get("embedding")
                if not embedding:
                    raise ValueError("Empty embedding from Ollama")

                return embedding
        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            raise

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Range: 0-1 (1 = identical, 0 = orthogonal)
        """
        if not vec1 or not vec2:
            return 0.0

        if len(vec1) != len(vec2):
            # Pad or truncate to match
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a ** 2 for a in vec1) ** 0.5
        norm2 = sum(b ** 2 for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def index_document(
        self,
        doc_id: int,
    ) -> bool:
        """
        Generate and store embedding for a document.

        Prepares document for RAG search.
        """
        doc = self.repo.get_document_by_id(doc_id)
        if not doc:
            raise Exception(f"Document {doc_id} not found")

        try:
            # Generate embedding
            embedding = await self._get_embedding(doc.content)

            # Store embedding
            self.repo.update_document(
                doc_id,
                embedding=embedding,
                is_embedded=1,
                is_indexed=1,
            )

            logger.info(f"✅ Document {doc_id} indexed for RAG")
            return True
        except Exception as e:
            logger.error(f"Failed to index document {doc_id}: {e}")
            self.repo.update_document(
                doc_id,
                is_indexed=0,
            )
            return False


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service(db: Session) -> RAGService:
    """Get or create RAGService instance."""
    return RAGService(db)
