"""Serviço de classificação de textos como judiciais ou não.

Utilizado para validar se um email/documento é relacionado a processos judiciais.
Implementação simples baseada em keywords para fase inicial.
"""

import logging
import re
from decimal import Decimal
from typing import Tuple

logger = logging.getLogger(__name__)

JUDICIAL_KEYWORDS = [
    # Órgãos judiciais
    r"tribunal\b",
    r"vara\b",
    r"juizado",
    r"supremo tribunal",
    r"corte",
    r"câmara",
    r"ministério público",
    r"ofício\b",
    # Processos
    r"número do processo",
    r"autos\b",
    r"cláusula processual",
    r"recurso\b",
    r"apelação",
    r"sentença",
    r"decisão",
    r"liminar",
    # Partes
    r"autor\b",
    r"réu\b",
    r"reclamante",
    r"reclamado",
    r"agravante",
    r"agravado",
    # Operações
    r"protocolo",
    r"intimação",
    r"mandado",
    r"execução",
    r"arresto",
    r"penhora",
    # Leis/Códigos
    r"código de processo",
    r"código penal",
    r"código civil",
    r"cpc\b",
    r"cpp\b",
    r"clt\b",
    # Documentos
    r"certidão",
    r"contra-razão",
    r"petição",
    r"memorial",
    # Prazos e datas
    r"prazo\b",
    r"semestre",
    r"trimestre",
    r"decadência",
    r"prescrição",
    # Pessoas
    r"advogado",
    r"juiz",
    r"desembargador",
    r"promotor",
    r"procurador",
]

COMPILED_REGEX = re.compile("|".join(JUDICIAL_KEYWORDS), re.IGNORECASE)
CNJ_REGEX = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


class JudicialClassificationService:
    """Classifica se um texto é relacionado a matéria judicial."""

    @staticmethod
    def classificar(texto: str) -> Tuple[bool, Decimal]:
        """Classifica um texto como judicial ou não.

        Args:
            texto: Texto a classificar (assunto + corpo do email, por exemplo)

        Retorna:
            (eh_judicial, confianca)
            - eh_judicial: bool indicating if text is judicial
            - confianca: Decimal from 0.0 to 1.0 indicating confidence
        """
        if not texto:
            return False, Decimal("0.0")

        # Buscar palavras-chave judiciais
        matches = COMPILED_REGEX.findall(texto)

        if not matches:
            return False, Decimal("0.0")

        # Confiança baseada em densidade de palavras-chave
        # Máximo de 1.0, mínimo de 0.5 se houver match
        palavras = texto.lower().split()
        densidade = min(len(matches) / max(len(palavras), 1), 1.0)

        # Se houver matches, confiança mínima é 0.6
        confianca = Decimal(str(max(densidade, 0.6)))

        logger.debug(
            f"Classificação judicial: matches={len(matches)}, "
            f"palavras={len(palavras)}, confiança={confianca}"
        )

        return True, confianca

    @staticmethod
    def extrair_dados_processuais(texto: str) -> dict:
        """Extrai dados processuais do texto (número de processo CNJ, etc).

        Args:
            texto: Texto do email

        Retorna:
            Dict com dados encontrados: {
                "numero_processo": "1234567-89.0123.4.56.7890" ou None,
                "tem_processo": bool
            }
        """
        if not texto:
            return {"numero_processo": None, "tem_processo": False}

        # Buscar número de processo CNJ (padrão: NNNNNNN-DD.AAAA.J.TT.OOOO)
        match = CNJ_REGEX.search(texto)

        if match:
            return {
                "numero_processo": match.group(),
                "tem_processo": True
            }

        return {"numero_processo": None, "tem_processo": False}
