"""APIs públicas gratuitas integradas ao Perito (catálogo public-apis/public-apis).

Complementa indices_bcb.py (que cobre os índices de atualização monetária):
- Feriados nacionais + prazos em dias úteis (CPC 219)  → BrasilAPI
- CNPJ (partes/empresas em cadastro)                    → BrasilAPI, fallback ReceitaWS
- CEP (endereços de diligência/cadastro)                → BrasilAPI, fallback ViaCEP
- Câmbio tempo real (USD-BRL, EUR-BRL, BTC-BRL...)      → AwesomeAPI
- PTAX oficial do dólar por data (perícias c/ moeda)    → BCB Olinda
- Tabela FIPE (avaliação de veículos em perícias)       → parallelum.com.br
- Municípios por UF (comarcas)                          → IBGE

Todas sem chave de API. Cache TTL em memória para respeitar rate limits.
"""
import logging
import re
import time
from datetime import date, datetime, timedelta

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 20
_cache: dict = {}  # chave -> (expira_em, valor)


def _cacheado(chave: str, ttl_s: int, fn):
    agora = time.time()
    hit = _cache.get(chave)
    if hit and hit[0] > agora:
        return hit[1]
    valor = fn()
    _cache[chave] = (agora + ttl_s, valor)
    return valor


def _get_json(url: str, **kwargs):
    r = requests.get(url, timeout=_TIMEOUT, **kwargs)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- feriados/prazos

def feriados(ano: int) -> list[dict]:
    """Feriados nacionais do ano (BrasilAPI). Cache 24h."""
    return _cacheado(f"feriados:{ano}", 86400,
                     lambda: _get_json(f"https://brasilapi.com.br/api/feriados/v1/{ano}"))


def _datas_feriados(anos: set[int]) -> set[date]:
    datas = set()
    for ano in anos:
        for f in feriados(ano):
            datas.add(datetime.strptime(f["date"], "%Y-%m-%d").date())
    return datas


def calcular_prazo(inicio: date, dias: int, uteis: bool = True) -> dict:
    """Data fatal de um prazo a partir de `inicio` (exclusivo, CPC 224).
    `uteis=True` conta só dias úteis (CPC 219), pulando fins de semana e
    feriados NACIONAIS (feriados forenses locais não entram — conferir no TJ)."""
    fers = _datas_feriados({inicio.year, inicio.year + 1}) if uteis else set()
    atual, contados = inicio, 0
    while contados < dias:
        atual += timedelta(days=1)
        if uteis and (atual.weekday() >= 5 or atual in fers):
            continue
        contados += 1
    # prorroga se cair em dia não útil (CPC 224 §1º)
    while uteis and (atual.weekday() >= 5 or atual in fers):
        atual += timedelta(days=1)
    return {
        "inicio": inicio.isoformat(), "dias": dias,
        "contagem": "dias úteis (CPC 219)" if uteis else "dias corridos",
        "data_fatal": atual.isoformat(),
        "aviso": "Feriados forenses/locais do tribunal não incluídos — conferir.",
    }


def dias_uteis_entre(inicio: date, fim: date) -> int:
    """Quantos dias úteis existem entre inicio (exclusivo) e fim (inclusivo)."""
    fers = _datas_feriados({inicio.year, fim.year})
    n, atual = 0, inicio
    while atual < fim:
        atual += timedelta(days=1)
        if atual.weekday() < 5 and atual not in fers:
            n += 1
    return n


# ---------------------------------------------------------------- cadastro

def consultar_cnpj(cnpj: str) -> dict:
    """Dados cadastrais por CNPJ — BrasilAPI, fallback ReceitaWS. Cache 24h."""
    cnpj = re.sub(r"\D", "", cnpj)
    if len(cnpj) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos")

    def _buscar():
        try:
            d = _get_json(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}")
            return {
                "fonte": "brasilapi", "cnpj": cnpj,
                "razao_social": d.get("razao_social"),
                "nome_fantasia": d.get("nome_fantasia"),
                "situacao": d.get("descricao_situacao_cadastral"),
                "natureza_juridica": d.get("natureza_juridica"),
                "capital_social": d.get("capital_social"),
                "logradouro": d.get("logradouro"), "numero": d.get("numero"),
                "bairro": d.get("bairro"), "municipio": d.get("municipio"),
                "uf": d.get("uf"), "cep": d.get("cep"),
                "cnae_principal": d.get("cnae_fiscal_descricao"),
                "socios": [{"nome": q.get("nome_socio"), "qualificacao": q.get("qualificacao_socio")}
                           for q in (d.get("qsa") or [])],
            }
        except Exception as e:
            logger.warning(f"BrasilAPI CNPJ falhou ({e}), tentando ReceitaWS")
            d = _get_json(f"https://receitaws.com.br/v1/cnpj/{cnpj}")
            if d.get("status") == "ERROR":
                raise ValueError(d.get("message", "CNPJ não encontrado"))
            return {
                "fonte": "receitaws", "cnpj": cnpj,
                "razao_social": d.get("nome"), "nome_fantasia": d.get("fantasia"),
                "situacao": d.get("situacao"), "natureza_juridica": d.get("natureza_juridica"),
                "capital_social": d.get("capital_social"),
                "logradouro": d.get("logradouro"), "numero": d.get("numero"),
                "bairro": d.get("bairro"), "municipio": d.get("municipio"),
                "uf": d.get("uf"), "cep": d.get("cep"),
                "cnae_principal": (d.get("atividade_principal") or [{}])[0].get("text"),
                "socios": [{"nome": q.get("nome"), "qualificacao": q.get("qual")}
                           for q in (d.get("qsa") or [])],
            }

    return _cacheado(f"cnpj:{cnpj}", 86400, _buscar)


def consultar_cep(cep: str) -> dict:
    """Endereço por CEP — BrasilAPI v2, fallback ViaCEP. Cache 24h."""
    cep = re.sub(r"\D", "", cep)
    if len(cep) != 8:
        raise ValueError("CEP deve ter 8 dígitos")

    def _buscar():
        try:
            d = _get_json(f"https://brasilapi.com.br/api/cep/v2/{cep}")
            return {"fonte": "brasilapi", "cep": cep, "uf": d.get("state"),
                    "cidade": d.get("city"), "bairro": d.get("neighborhood"),
                    "logradouro": d.get("street")}
        except Exception as e:
            logger.warning(f"BrasilAPI CEP falhou ({e}), tentando ViaCEP")
            d = _get_json(f"https://viacep.com.br/ws/{cep}/json/")
            if d.get("erro"):
                raise ValueError("CEP não encontrado")
            return {"fonte": "viacep", "cep": cep, "uf": d.get("uf"),
                    "cidade": d.get("localidade"), "bairro": d.get("bairro"),
                    "logradouro": d.get("logradouro")}

    return _cacheado(f"cep:{cep}", 86400, _buscar)


def municipios(uf: str) -> list[dict]:
    """Municípios da UF (IBGE) — para cadastro de comarcas. Cache 7 dias."""
    uf = uf.strip().upper()
    return _cacheado(f"mun:{uf}", 7 * 86400, lambda: [
        {"id": m["id"], "nome": m["nome"]}
        for m in _get_json(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios")
    ])


# ---------------------------------------------------------------- moedas

def cambio(par: str = "USD-BRL") -> dict:
    """Cotação em tempo real (AwesomeAPI). Aceita USD-BRL, EUR-BRL, BTC-BRL etc.
    Cache 5min."""
    par = par.strip().upper()
    if not re.fullmatch(r"[A-Z]{3,4}-[A-Z]{3,4}", par):
        raise ValueError("Par inválido — use o formato USD-BRL")

    def _buscar():
        d = _get_json(f"https://economia.awesomeapi.com.br/json/last/{par}")
        v = d[par.replace("-", "")]
        return {"par": par, "compra": v.get("bid"), "venda": v.get("ask"),
                "maxima": v.get("high"), "minima": v.get("low"),
                "data": v.get("create_date"), "fonte": "awesomeapi"}

    return _cacheado(f"cambio:{par}", 300, _buscar)


def ptax_dolar(dia: date) -> dict:
    """Cotação PTAX OFICIAL do dólar (BCB Olinda) para a data — é a cotação que
    perícia judicial deve usar. Se não houver (fim de semana/feriado), informa."""
    data_fmt = dia.strftime("%m-%d-%Y")
    url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
           f"CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{data_fmt}'&$format=json")

    def _buscar():
        valores = _get_json(url).get("value") or []
        if not valores:
            return {"data": dia.isoformat(), "cotacao": None,
                    "aviso": "Sem PTAX na data (fim de semana/feriado) — use o dia útil anterior."}
        v = valores[-1]
        return {"data": dia.isoformat(), "compra": v.get("cotacaoCompra"),
                "venda": v.get("cotacaoVenda"), "momento": v.get("dataHoraCotacao"),
                "fonte": "BCB PTAX"}

    return _cacheado(f"ptax:{dia.isoformat()}", 86400, _buscar)


# ---------------------------------------------------------------- FIPE

_FIPE = "https://parallelum.com.br/fipe/api/v1"


def fipe_marcas(tipo: str = "carros") -> list[dict]:
    """Marcas FIPE. tipo: carros | motos | caminhoes. Cache 7 dias."""
    if tipo not in ("carros", "motos", "caminhoes"):
        raise ValueError("tipo deve ser carros, motos ou caminhoes")
    return _cacheado(f"fipe:{tipo}", 7 * 86400, lambda: _get_json(f"{_FIPE}/{tipo}/marcas"))


def fipe_modelos(tipo: str, marca_id: str) -> list[dict]:
    return _cacheado(f"fipe:{tipo}:{marca_id}", 7 * 86400,
                     lambda: _get_json(f"{_FIPE}/{tipo}/marcas/{marca_id}/modelos").get("modelos", []))


def fipe_anos(tipo: str, marca_id: str, modelo_id: str) -> list[dict]:
    return _get_json(f"{_FIPE}/{tipo}/marcas/{marca_id}/modelos/{modelo_id}/anos")


def fipe_valor(tipo: str, marca_id: str, modelo_id: str, ano_id: str) -> dict:
    """Valor FIPE do veículo — referência oficial para laudo de avaliação."""
    return _get_json(f"{_FIPE}/{tipo}/marcas/{marca_id}/modelos/{modelo_id}/anos/{ano_id}")
