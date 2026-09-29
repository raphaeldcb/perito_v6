"""
RAG layer with pattern search + manual fallback.

Task 2: Search for patterns in previous laudos OR accept manual input if no pattern exists.

Features:
- Searches for previous laudos of same tipo_laudo by perito_id
- Extracts pattern: sections (from markdown ##), top 10 terms, style
- Accepts manual input fields (dados_planilha, honorarios, observacoes)
- Returns flexible structure with origin (rag, manual, hibrido)
"""
import re
from typing import Dict, Any, Optional, List
from collections import Counter
from sqlalchemy.orm import Session
from app.models import Laudo, LaudoVersao


class LaudoRAGHibrido:
    """RAG hybrid layer: pattern search + manual fallback."""

    def __init__(self):
        """Initialize the RAG hybrid service."""
        self.section_pattern = re.compile(r'^## (.+)$', re.MULTILINE)
        self.word_pattern = re.compile(r'\b\w+\b', re.IGNORECASE)
        self.known_manual_fields = {"dados_planilha", "honorarios", "observacoes"}

    def buscar_ou_aceitar_manual(
        self,
        db: Session,
        tipo_laudo: str,
        perito_id: int,
        dados_entrada: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Search for patterns in previous laudos or accept manual input.

        Args:
            db: Database session
            tipo_laudo: Type of laudo (e.g., "contabil", "insalubridade")
            perito_id: ID of the perito
            dados_entrada: Flexible input dictionary with custom fields

        Returns:
            Dict with keys:
            - origem: "rag" | "manual" | "hibrido"
            - padroes_rag: extracted pattern or None
              - secoes: list of section titles
              - termos_top_10: dict of top 10 terms with frequencies
              - estilo: description of style
            - dados_manuais: dict with known manual fields
            - campos_extras: dict with remaining extra fields
        """
        # Search for previous laudos
        padroes_rag = self._buscar_padroes(db, tipo_laudo, perito_id)

        # Extract manual fields
        dados_manuais, campos_extras = self._extrair_manual_fields(dados_entrada)

        # Decide origin
        origem = self._decidir_origem(padroes_rag, dados_manuais)

        return {
            "origem": origem,
            "padroes_rag": padroes_rag,
            "dados_manuais": dados_manuais,
            "campos_extras": campos_extras,
        }

    def _buscar_padroes(
        self,
        db: Session,
        tipo_laudo: str,
        perito_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Search for patterns in last 10 laudos of same type by perito.

        Args:
            db: Database session
            tipo_laudo: Type of laudo
            perito_id: ID of the perito

        Returns:
            Dict with secoes, termos_top_10, estilo, or None if no laudos found
        """
        # Query last 10 laudos of same type by perito
        laudos = db.query(Laudo).filter(
            Laudo.tipo_laudo == tipo_laudo,
            Laudo.perito_id == perito_id
        ).order_by(Laudo.data_criacao.desc()).limit(10).all()

        if not laudos:
            return None

        # Extract pattern from laudos
        secoes = self._extrair_secoes(laudos)
        termos_top_10 = self._extrair_termos_top_10(laudos)
        estilo = self._descrever_estilo(laudos, secoes)

        return {
            "secoes": secoes,
            "termos_top_10": termos_top_10,
            "estilo": estilo,
        }

    def _extrair_secoes(self, laudos: List[Laudo]) -> List[str]:
        """
        Extract section titles (## headings) from laudo markdown.

        Args:
            laudos: List of laudo objects

        Returns:
            List of unique section titles
        """
        secoes_set = set()

        for laudo in laudos:
            if not laudo.versoes:
                continue

            # Get the latest version
            versao = sorted(laudo.versoes, key=lambda v: v.numero_versao, reverse=True)[0]

            if not versao.conteudo_markdown:
                continue

            # Find all section headers (## Title)
            matches = self.section_pattern.findall(versao.conteudo_markdown)
            for match in matches:
                secoes_set.add(match.strip())

        return sorted(list(secoes_set))

    def _extrair_termos_top_10(self, laudos: List[Laudo]) -> Dict[str, int]:
        """
        Extract top 10 most frequent words from laudo content.

        Args:
            laudos: List of laudo objects

        Returns:
            Dict with top 10 words and frequencies
        """
        # Collect all words
        all_words = []

        for laudo in laudos:
            if not laudo.versoes:
                continue

            versao = sorted(laudo.versoes, key=lambda v: v.numero_versao, reverse=True)[0]

            if not versao.conteudo_markdown:
                continue

            # Extract words
            words = self.word_pattern.findall(versao.conteudo_markdown)
            # Filter: keep only words > 3 chars, lowercase
            words = [w.lower() for w in words if len(w) > 3 and w.isalpha()]
            all_words.extend(words)

        # Count word frequency
        if not all_words:
            return {}

        word_counts = Counter(all_words)

        # Get top 10
        top_10 = dict(word_counts.most_common(10))

        return top_10

    def _descrever_estilo(
        self,
        laudos: List[Laudo],
        secoes: List[str]
    ) -> str:
        """
        Describe the style of laudos based on structure and content.

        Args:
            laudos: List of laudo objects
            secoes: List of section titles

        Returns:
            String description of style
        """
        # Calculate characteristics
        total_laudos = len(laudos)

        avg_length = 0
        if laudos and laudos[0].versoes:
            lengths = []
            for laudo in laudos:
                if laudo.versoes:
                    versao = sorted(laudo.versoes, key=lambda v: v.numero_versao, reverse=True)[0]
                    if versao.conteudo_markdown:
                        lengths.append(len(versao.conteudo_markdown))
            if lengths:
                avg_length = sum(lengths) / len(lengths)

        num_sections = len(secoes)

        # Build description
        estilo = f"Estruturado em {num_sections} seções"

        if avg_length < 2000:
            estilo += ", estilo conciso"
        elif avg_length > 10000:
            estilo += ", estilo detalhado"
        else:
            estilo += ", estilo moderado"

        estilo += f" (baseado em {total_laudos} laudos anteriores)"

        return estilo

    def _extrair_manual_fields(
        self,
        dados_entrada: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract known manual fields and separate extras.

        Args:
            dados_entrada: Flexible input dictionary

        Returns:
            Tuple of (dados_manuais, campos_extras)
        """
        dados_manuais = {}
        campos_extras = {}

        for key, value in dados_entrada.items():
            if key in self.known_manual_fields:
                dados_manuais[key] = value
            else:
                campos_extras[key] = value

        return dados_manuais, campos_extras

    def _decidir_origem(
        self,
        padroes_rag: Optional[Dict[str, Any]],
        dados_manuais: Dict[str, Any]
    ) -> str:
        """
        Decide the origin: rag, manual, or hibrido.

        Args:
            padroes_rag: Pattern extracted from RAG search (or None)
            dados_manuais: Manual fields extracted

        Returns:
            One of: "rag", "manual", "hibrido"
        """
        tem_padrao = padroes_rag is not None and (
            padroes_rag.get("secoes") or padroes_rag.get("termos_top_10")
        )
        tem_manual = len(dados_manuais) > 0

        if tem_padrao and tem_manual:
            return "hibrido"
        elif tem_padrao:
            return "rag"
        else:
            return "manual"
