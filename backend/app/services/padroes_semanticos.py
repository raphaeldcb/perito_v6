"""Tokenização de padrões semânticos (Task 7 do plano
docs/superpowers/plans/2026_001-ferramenta_calculo_v2.md).

Uma regra semântica descreve, em texto, como montar a timeline de um cálculo
a partir de marcos processuais ainda sem data confirmada — ex.:
"Poupança até [SENTENÇA], IPCA depois". `tokenizar_regra` extrai os tokens
([SENTENÇA], [CITAÇÃO], [HOJE] etc — inclui acentuação PT-BR); depois que o
Qwen (Task 8) resolve as datas reais desses marcos nos autos,
`substituir_tokens` monta a lista de períodos ({"indexador", "inicio"/"fim"})
no mesmo formato de `timeline` consumido por POST /calcular.
"""
import re
from typing import Dict, List

# Tokens são MAIÚSCULOS e podem conter acentuação/cedilha PT-BR
# (ex.: [SENTENÇA], [CITAÇÃO]) além de underscore para nomes compostos.
TOKEN_PATTERN = re.compile(r"\[([A-ZÀ-Ÿ_]+)\]")


def tokenizar_regra(regra_semantica: str) -> List[str]:
    """Extrai, sem duplicatas, os tokens [TOKEN] de uma regra semântica."""
    return list(dict.fromkeys(TOKEN_PATTERN.findall(regra_semantica)))


def substituir_tokens(regra: str, datas_confirmadas: Dict[str, str]) -> List[dict]:
    """Substitui os tokens de uma regra pelas datas confirmadas.

    A regra é dividida em segmentos por vírgula; cada segmento vira um
    período com "indexador" (primeira palavra do segmento) e "inicio"/"fim":

    - 1 token + "até" no segmento (ex. "Poupança até [SENTENÇA]") -> fim.
    - 1 token sem "até" (ex. "IPCA a partir de [SENTENÇA]") -> inicio.
    - 2 tokens (ex. "IPCA de [SENTENÇA] a [HOJE]") -> inicio e fim explícitos.
    - 0 tokens (ex. "IPCA depois") -> herda o "inicio" do fim do período
      anterior (continuação natural da timeline).
    """
    periodos: List[dict] = []
    data_corrente = None

    for segmento in regra.split(","):
        segmento = segmento.strip()
        if not segmento:
            continue

        indexador_match = re.match(r"(\w+)", segmento)
        indexador = indexador_match.group(1) if indexador_match else ""
        tokens = TOKEN_PATTERN.findall(segmento)
        periodo = {"indexador": indexador}

        if len(tokens) >= 2:
            periodo["inicio"] = datas_confirmadas.get(tokens[0])
            periodo["fim"] = datas_confirmadas.get(tokens[1])
            data_corrente = periodo["fim"]
        elif len(tokens) == 1:
            data = datas_confirmadas.get(tokens[0])
            if "até" in segmento:
                periodo["fim"] = data
            else:
                periodo["inicio"] = data
            data_corrente = data
        else:
            periodo["inicio"] = data_corrente

        periodos.append(periodo)

    return periodos
