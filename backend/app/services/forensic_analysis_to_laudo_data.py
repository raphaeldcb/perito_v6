"""
Extrator de Dados de Análise Forense → Placeholders DOCX.

Extrai dados de um objeto ForensicAnalysis e transforma em dicionário
com chaves que correspondem aos placeholders do template DOCX.

Formato codigo_laudo: L + YYYYMMDD + analysis_id[:8]
"""
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ForensicAnalysisToLaudoData:
    """
    Extrai dados de ForensicAnalysis e mapeia para placeholders DOCX.

    Métodos:
    - extract(analysis, user_name) -> Dict[str, str]
        Extrai todos os dados necessários para preenchimento do template
    - _generate_codigo_laudo(analysis_id, created_at) -> str
        Gera codigo_laudo no formato L + YYYYMMDD + id[:8]
    - _map_veredicto_to_risco(veredicto) -> str
        Mapeia veredicto para nível de risco
    - _analyze_artifacts(resultado_json) -> dict
        Conta achados por nível (CRITICO, ALERTA, INFORMATIVO)
    - _format_file_size(bytes_value) -> str
        Converte bytes para KB formatado
    - _format_confidence(score) -> str
        Formata score (0.0-1.0) como percentual
    - _format_date_br(dt) -> str
        Formata datetime como dd/mm/yyyy
    - _format_time(dt) -> str
        Formata datetime como HH:MM
    """

    def extract(
        self,
        analysis: "ForensicAnalysis",
        user_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Extrai dados de ForensicAnalysis para dicionário de placeholders DOCX.

        Args:
            analysis: Objeto ForensicAnalysis com resultados da análise
            user_name: Nome do perito/contratante (opcional)

        Returns:
            Dict[str, str] com chaves como: codigo_laudo, contratante, arquivo_nome, etc.
        """
        # Map veredicto to risk level
        risk_level = self._map_veredicto_to_risco(analysis.veredicto_final or "REVISAR")

        # Analyze findings/achados from resultado_json
        achados_counts = self._analyze_artifacts(analysis.resultado_json)

        # Format file size
        file_size_kb = self._format_file_size(analysis.arquivo_tamanho_bytes or 0)

        # Format confidence as percentage
        confidence_pct = self._format_confidence(analysis.confianca_consenso or 0.0)

        # Format date/time in Brazilian format
        data_analise = self._format_date_br(analysis.timestamp_criacao)
        hora_analise = self._format_time(analysis.timestamp_criacao)

        # Calculate total analysis time in minutes
        tempo_minutos = self._calculate_duration_minutes(
            analysis.timestamp_criacao,
            analysis.timestamp_conclusao
        )

        # Generate codigo_laudo: L + YYYYMMDD + id[:8]
        codigo_laudo = self._generate_codigo_laudo(
            analysis.id,
            analysis.timestamp_criacao
        )

        # Build the data dictionary with all placeholder keys
        data = {
            # Identificação do laudo
            'codigo_laudo': codigo_laudo,
            'contratante': user_name or 'Perito (Análise Automática)',

            # Dados do arquivo analisado
            'arquivo_nome': analysis.arquivo_nome or 'N/A',
            'arquivo_mime': analysis.arquivo_tipo or 'application/octet-stream',
            'arquivo_tamanho_kb': file_size_kb,
            'arquivo_hash': analysis.arquivo_hash_md5 or 'N/A',

            # Resultados da análise
            'confianca': confidence_pct,
            'nivel_risco': risk_level,
            'veredicto': analysis.veredicto_final or 'REVISAR',

            # Data e hora
            'data_analise': data_analise,
            'hora_analise': hora_analise,
            'tempo_total_minutos': str(tempo_minutos),

            # Achados/Findings por nível
            'achados_criticos': str(achados_counts['criticos']),
            'achados_alertas': str(achados_counts['alertas']),
            'achados_informativos': str(achados_counts['informativos']),
            'total_achados': str(achados_counts['total']),
        }

        return data

    def _generate_codigo_laudo(self, analysis_id: int, created_at: Optional[datetime]) -> str:
        """
        Gera codigo_laudo no formato: L + YYYYMMDD + id[:8]

        Exemplo: L20260807 + "00012345" = L202608070000c491
        (onde 0000c491 é a representação hex do ID)

        Args:
            analysis_id: ID da análise
            created_at: Data de criação

        Returns:
            Código laudo formatado
        """
        if not created_at:
            created_at = datetime.utcnow()

        # Format date as YYYYMMDD
        data_part = created_at.strftime("%Y%m%d")

        # Format ID as 8-char hex (without 0x prefix)
        id_part = f"{analysis_id:08x}"

        # Combine: L + YYYYMMDD + id_hex
        codigo = f"L{data_part}{id_part}"

        return codigo

    def _map_veredicto_to_risco(self, veredicto: str) -> str:
        """
        Mapeia veredicto para nível de risco (BAIXO/MÉDIO/ALTO).

        Mapeamento:
        - APROVADO → BAIXO
        - REVISAR → MÉDIO
        - REJEITADO → ALTO

        Args:
            veredicto: String com veredicto (APROVADO/REJEITADO/REVISAR/etc)

        Returns:
            Nível de risco: BAIXO, MÉDIO, ou ALTO
        """
        veredicto_upper = (veredicto or "REVISAR").upper().strip()

        mapping = {
            "APROVADO": "BAIXO",
            "REJEITADO": "ALTO",
            "REVISAR": "MÉDIO",
            "INCONCLUSIVO": "MÉDIO",
        }

        return mapping.get(veredicto_upper, "MÉDIO")

    def _analyze_artifacts(self, resultado_json: Optional[dict]) -> dict:
        """
        Analisa achados (findings) no resultado JSON e conta por nível.

        Procura por chave 'achados' que contém lista de dicts com 'nivel':
        [
            {"nivel": "CRITICO", "descricao": "..."},
            {"nivel": "ALERTA", "descricao": "..."},
            {"nivel": "INFORMATIVO", "descricao": "..."},
        ]

        Args:
            resultado_json: Dicionário com resultado da análise

        Returns:
            Dict com contagens: {'criticos': N, 'alertas': N, 'informativos': N, 'total': N}
        """
        counts = {
            'criticos': 0,
            'alertas': 0,
            'informativos': 0,
            'total': 0,
        }

        if not resultado_json or not isinstance(resultado_json, dict):
            return counts

        achados = resultado_json.get('achados', [])
        if not achados or not isinstance(achados, list):
            return counts

        for achado in achados:
            if not isinstance(achado, dict):
                continue

            nivel = (achado.get('nivel') or "").upper().strip()

            if nivel == "CRITICO":
                counts['criticos'] += 1
            elif nivel == "ALERTA":
                counts['alertas'] += 1
            elif nivel == "INFORMATIVO":
                counts['informativos'] += 1

            counts['total'] += 1

        return counts

    def _format_file_size(self, bytes_value: int) -> str:
        """
        Converte tamanho em bytes para formato legível em KB.

        Args:
            bytes_value: Tamanho em bytes

        Returns:
            String formatada, ex: "100 KB" ou "1.5 MB"
        """
        if bytes_value is None or bytes_value == 0:
            return "0 KB"

        # Convert to KB
        kb = bytes_value / 1024

        if kb < 1024:
            # Show in KB
            return f"{kb:.0f} KB"
        else:
            # Show in MB
            mb = kb / 1024
            return f"{mb:.2f} MB"

    def _format_confidence(self, score: float) -> str:
        """
        Formata score de confiança (0.0-1.0) como percentual.

        Args:
            score: Score entre 0.0 e 1.0

        Returns:
            String formatada, ex: "95.00%" ou "87.65%"
        """
        if score is None or score < 0:
            return "0.00%"

        # Clamp to 1.0
        score = min(score, 1.0)

        # Convert to percentage
        percentage = score * 100

        return f"{percentage:.2f}%"

    def _format_date_br(self, dt: Optional[datetime]) -> str:
        """
        Formata datetime como data em padrão brasileiro: dd/mm/yyyy.

        Args:
            dt: Objeto datetime

        Returns:
            String formatada, ex: "07/08/2026"
        """
        if dt is None:
            return "01/01/1900"

        return dt.strftime("%d/%m/%Y")

    def _format_time(self, dt: Optional[datetime]) -> str:
        """
        Formata datetime como hora: HH:MM.

        Args:
            dt: Objeto datetime

        Returns:
            String formatada, ex: "10:30"
        """
        if dt is None:
            return "00:00"

        return dt.strftime("%H:%M")

    def _calculate_duration_minutes(
        self,
        start: Optional[datetime],
        end: Optional[datetime]
    ) -> int:
        """
        Calcula duração em minutos entre dois datetimes.

        Args:
            start: Timestamp inicial
            end: Timestamp final

        Returns:
            Duração em minutos (inteiro)
        """
        if not start or not end:
            return 0

        delta = end - start
        return int(delta.total_seconds() / 60)
