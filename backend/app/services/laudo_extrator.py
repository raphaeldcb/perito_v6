"""
Complete process data extraction with folha (page) indexing.

Task 1: Extract ALL process documents without truncation, with folha indexing
for use in the Laudo V2 pipeline.

Features:
- Extracts complete document content (no 8KB truncation)
- Indexes folhas (pages) by detecting patterns like "Folha XX"
- Supports unlimited custom fields in documents
- Returns complete metadata + text concatenation
"""
import re
from typing import Dict, List, Any, Optional
from app.models import Processo


class LaudoExtrator:
    """Extract complete processo data with folha indexing."""

    def __init__(self):
        """Initialize the extrator."""
        self.folha_pattern = re.compile(r'(?:Folha|fl\.)\s+(\d+)', re.IGNORECASE)

    def extrair_processo(self, processo: Processo) -> Dict[str, Any]:
        """
        Extract complete process data from a Processo model.

        Args:
            processo: Processo model with documentos and metadata

        Returns:
            Dict with keys:
            - documentos: List[Dict] with indice, nome, fls, conteudo (complete, no truncation)
            - metadata: Dict with numero, partes, vara, tipo
            - texto_completo: Concatenated full text
            - folhas_index: Dict mapping "fls_N" → section text
        """
        # Extract documents (preserve all content, no truncation)
        documentos_list = self._extrair_documentos(processo)

        # Extract metadata
        metadata = self._extrair_metadata(processo)

        # Concatenate all document content
        texto_completo = self._concatenar_texto(documentos_list)

        # Index folhas from the complete text
        folhas_index = self._indexar_folhas(texto_completo)

        return {
            "documentos": documentos_list,
            "metadata": metadata,
            "texto_completo": texto_completo,
            "folhas_index": folhas_index,
        }

    def _extrair_documentos(self, processo: Processo) -> List[Dict[str, Any]]:
        """
        Extract all documents with complete content.

        Args:
            processo: Processo model

        Returns:
            List of documents with all fields preserved, content not truncated
        """
        if not processo.documentos:
            return []

        documentos = []
        for doc in processo.documentos:
            if isinstance(doc, dict):
                # Preserve all fields from the original document
                doc_copy = dict(doc)
                # Ensure required fields exist
                if "indice" not in doc_copy and "conteudo" in doc_copy:
                    doc_copy["indice"] = len(documentos) + 1
                if "nome" not in doc_copy:
                    doc_copy["nome"] = f"Documento {len(documentos) + 1}"
                if "fls" not in doc_copy:
                    doc_copy["fls"] = ""

                # Ensure conteudo is complete string (no truncation)
                if "conteudo" in doc_copy:
                    conteudo = doc_copy["conteudo"]
                    if isinstance(conteudo, str):
                        doc_copy["conteudo"] = conteudo
                    else:
                        doc_copy["conteudo"] = str(conteudo)

                documentos.append(doc_copy)

        return documentos

    def _extrair_metadata(self, processo: Processo) -> Dict[str, Any]:
        """
        Extract complete metadata from processo.

        Args:
            processo: Processo model

        Returns:
            Dict with numero, partes (reqte/reqdo), vara, tipo
        """
        return {
            "numero": processo.numero_cnj,
            "partes": {
                "reqte": processo.autor or "",
                "reqdo": processo.reu or "",
            },
            "vara": processo.vara or "",
            "tipo": processo.especialidade or "",
        }

    def _concatenar_texto(self, documentos: List[Dict[str, Any]]) -> str:
        """
        Concatenate all document content into single text.

        Args:
            documentos: List of documents

        Returns:
            Concatenated complete text
        """
        partes = []
        for doc in documentos:
            conteudo = doc.get("conteudo", "")
            if conteudo:
                partes.append(str(conteudo))

        return "\n\n".join(partes)

    def _indexar_folhas(self, texto_completo: str) -> Dict[str, str]:
        """
        Index folhas by detecting "Folha XX" patterns in text.

        Args:
            texto_completo: Complete concatenated text

        Returns:
            Dict mapping "fls_N" → section text (content between Folha N and next Folha)
        """
        if not texto_completo:
            return {}

        folhas_index = {}

        # Find all folha markers and their positions
        matches = list(self.folha_pattern.finditer(texto_completo))

        if not matches:
            return folhas_index

        # For each folha match, extract text until the next folha
        for i, match in enumerate(matches):
            folha_num = match.group(1)
            folha_key = f"fls_{folha_num}"

            # Start position: beginning of this folha marker
            start_pos = match.start()

            # End position: beginning of next folha marker or end of text
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(texto_completo)

            # Extract section text
            section_text = texto_completo[start_pos:end_pos].strip()
            folhas_index[folha_key] = section_text

        return folhas_index

    def extrair_com_rag(
        self,
        processo: Processo,
        rag_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Extract processo data with RAG context (optional, for Task 2).

        Args:
            processo: Processo model
            rag_results: Optional RAG search results to include

        Returns:
            Extraction result with RAG context
        """
        resultado = self.extrair_processo(processo)
        if rag_results:
            resultado["rag_context"] = rag_results
        return resultado
