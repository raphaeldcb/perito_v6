"""Correção monetária pelo IPCA — índice oficial do Banco Central (série SGS 433).

Responde: "um caso que fiz hoje e levei X anos para receber, quanto me custou?"
Corrige um valor da data do serviço até a data de recebimento pela inflação
acumulada (IPCA), mostrando a perda pelo tempo.
"""
import logging
from datetime import date, datetime

import requests

logger = logging.getLogger(__name__)

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
_cache = {}  # (di, df) -> fator


def _mensal(data_ini: date, data_fim: date) -> list[dict]:
    di = data_ini.strftime("%d/%m/%Y")
    df = data_fim.strftime("%d/%m/%Y")
    chave = (di, df)
    if chave in _cache:
        return _cache[chave]
    resp = requests.get(BCB_URL, params={"formato": "json", "dataInicial": di, "dataFinal": df}, timeout=20)
    resp.raise_for_status()
    dados = resp.json()
    _cache[chave] = dados
    return dados


def corrigir(valor: float, data_inicio, data_fim=None) -> dict:
    """Corrige `valor` de data_inicio até data_fim (default hoje) pelo IPCA acumulado.

    Retorna: {valor_original, valor_corrigido, inflacao_pct, perda, meses}.
    """
    if isinstance(data_inicio, (datetime,)):
        data_inicio = data_inicio.date()
    if data_fim is None:
        data_fim = date.today()
    elif isinstance(data_fim, datetime):
        data_fim = data_fim.date()

    valor = float(valor or 0)
    try:
        serie = _mensal(data_inicio, data_fim)
    except Exception as e:
        return {"erro": f"Não foi possível obter o IPCA do Banco Central: {e}",
                "valor_original": valor, "valor_corrigido": valor}

    fator = 1.0
    for item in serie:
        try:
            fator *= (1 + float(item["valor"]) / 100)
        except (KeyError, ValueError):
            continue

    corrigido = round(valor * fator, 2)
    return {
        "valor_original": round(valor, 2),
        "valor_corrigido": corrigido,
        "inflacao_pct": round((fator - 1) * 100, 2),
        "perda": round(corrigido - valor, 2),
        "meses": len(serie),
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
    }
