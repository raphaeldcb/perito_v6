"""Calculadora de honorários (precificação) — replica a TABELA CALCULO PERÍCIA.xlsx.

valor do caso → valor com nota (imposto) → PIX / débito / crédito / parcelado.
Fórmulas exatas da planilha do Bruno:
  imposto: direto=0.16, ebook=0.03, modal=0.8*0.03+0.2*0.16=0.056
  valor_nota (PIX) = valor * (1 + imposto)
  débito  = round(valor_nota * 1.015)
  crédito = round(valor_nota * 1.03)
  parcela = floor(PMT(3.69% a.m., n, valor_nota))   |  total = parcela * n
"""
import math

IMPOSTOS = {"direto": 0.16, "ebook": 0.03, "modal": 0.8 * 0.03 + 0.2 * 0.16}


def _pmt(taxa: float, n: int, pv: float) -> float:
    if taxa == 0:
        return pv / n
    return pv * taxa / (1 - (1 + taxa) ** -n)


def calcular(valor_caso: float, tipo_imposto: str = "direto",
             parcelas: int = 12, taxa_parcela: float = 0.0369,
             sem_imposto: bool = False) -> dict:
    imposto = 0.0 if sem_imposto else IMPOSTOS.get(tipo_imposto, IMPOSTOS["direto"])
    valor_nota = valor_caso * (1 + imposto)          # PIX
    debito = round(valor_nota * 1.015)
    credito = round(valor_nota * 1.03)
    parcela = math.floor(_pmt(taxa_parcela, parcelas, valor_nota))
    return {
        "valor_caso": round(valor_caso, 2),
        "tipo_imposto": tipo_imposto,
        "sem_imposto": sem_imposto,
        "imposto_pct": round(imposto * 100, 2),
        "pix": round(valor_nota, 2),
        "debito": float(debito),
        "credito": float(credito),
        "parcelas": parcelas,
        "parcela": float(parcela),
        "total_parcelado": float(parcela * parcelas),
    }


# fator (multiplicador sobre o valor com nota) de cada forma
_FATOR = {"dinheiro": 1.0, "pix": 1.0, "debito": 1.015, "credito": 1.03}


def calcular_combinado(alocacoes: dict, tipo_imposto: str = "direto", parcelas: int = 12,
                       sem_imposto: bool = False, taxa_parcela: float = 0.0369) -> dict:
    """Combina várias formas numa cobrança só. `alocacoes` = quanto (R$ LÍQUIDO que o
    perito quer receber) o cliente paga em cada forma: {dinheiro, pix, debito, credito,
    parcelado}. Cada parte é 'brutada' pelo imposto (nota) + a taxa da forma. Retorna o
    detalhamento + total líquido (recebido) e total cobrado (o cliente paga)."""
    imposto = 0.0 if sem_imposto else IMPOSTOS.get(tipo_imposto, IMPOSTOS["direto"])
    itens, total_liq, total_cob = [], 0.0, 0.0

    for forma in ("dinheiro", "pix", "debito", "credito"):
        liq = float(alocacoes.get(forma) or 0)
        if liq <= 0:
            continue
        cobrado = liq * (1 + imposto) * _FATOR[forma]
        itens.append({"forma": forma, "liquido": round(liq, 2), "cobrado": round(cobrado, 2)})
        total_liq += liq
        total_cob += cobrado

    parc_liq = float(alocacoes.get("parcelado") or 0)
    if parc_liq > 0:
        com_nota = parc_liq * (1 + imposto)
        parcela = math.floor(_pmt(taxa_parcela, parcelas, com_nota))
        cobrado = float(parcela * parcelas)
        itens.append({"forma": "parcelado", "liquido": round(parc_liq, 2), "cobrado": cobrado,
                      "parcelas": parcelas, "parcela": float(parcela)})
        total_liq += parc_liq
        total_cob += cobrado

    return {
        "sem_imposto": sem_imposto, "tipo_imposto": tipo_imposto,
        "imposto_pct": round(imposto * 100, 2), "itens": itens,
        "total_liquido": round(total_liq, 2), "total_cobrado": round(total_cob, 2),
        "acrescimo": round(total_cob - total_liq, 2),
    }
