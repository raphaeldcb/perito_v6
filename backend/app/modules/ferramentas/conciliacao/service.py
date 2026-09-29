"""Motor de conciliação por VALOR CORRIGIDO.

Casa um crédito bancário com o honorário de um processo corrigindo o valor da
DATA DA PROPOSTA até a DATA DO CRÉDITO (regra do Bruno: sistema cego que procura só
o valor original falha — 1500 de 2015 pode entrar como ~2156 corrigido).
Índice padrão: IPCA-E (correção monetária judicial mais comum). Reusa indices_bcb.
"""
from datetime import date, datetime

from app.services import indices_bcb


def _to_date(d):
    if isinstance(d, date):
        return d
    for f in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(d)[:10], f).date()
        except ValueError:
            pass
    raise ValueError(f"data inválida: {d}")


def fator_correcao(indexador, data_ini, data_fim) -> float:
    """Fator acumulado do índice (produto de 1+pct/100) entre as duas datas."""
    di, df = _to_date(data_ini), _to_date(data_fim)
    serie = indices_bcb.serie_mensal(indexador, di, df) or {}
    ini, fim = date(di.year, di.month, 1), date(df.year, df.month, 1)
    fator = 1.0
    for ym, pct in sorted(serie.items()):
        try:
            ref = date(int(ym[:4]), int(ym[5:7]), 1)
        except Exception:
            continue
        if ini <= ref <= fim:
            fator *= (1 + float(pct) / 100)
    return fator


def corrigir(valor, data_ini, data_fim, indexador="IPCA") -> float:
    return round(float(valor) * fator_correcao(indexador, data_ini, data_fim), 2)


def conciliar_credito(valor, data_credito, candidatos, tolerancia=0.12, indexador="IPCA"):
    """Para cada candidato {honorario, data_proposta, ...}, corrige o honorário até a
    data do crédito e mede o quão perto o crédito está. Retorna ordenado por score."""
    V = float(valor)
    dc = _to_date(data_credito)
    out = []
    for c in candidatos:
        H = float(c.get("honorario") or 0)
        if H <= 0 or not c.get("data_proposta"):
            continue
        try:
            esp = corrigir(H, c["data_proposta"], dc, indexador)
        except Exception:
            continue
        if esp <= 0:
            continue
        dif = (V - esp) / esp
        item = {**c, "honorario": H, "valor_esperado": esp,
                "diferenca_pct": round(dif * 100, 2), "score": round(max(0.0, 1 - abs(dif)), 4),
                "casa": abs(dif) <= tolerancia}
        # regra do Bruno: crédito ~ valor ORIGINAL (sem correção) com proposta antiga
        # → provavelmente NÃO é esse caso (seria muito maior corrigido)
        try:
            anos = (dc - _to_date(c["data_proposta"])).days / 365.25
            if anos >= 3 and abs(V - H) / H <= 0.03:
                item["alerta"] = "valor ≈ original sem correção, mas proposta é antiga — provável OUTRO caso (recente)"
        except Exception:
            pass
        out.append(item)
    out.sort(key=lambda x: -x["score"])
    return out
