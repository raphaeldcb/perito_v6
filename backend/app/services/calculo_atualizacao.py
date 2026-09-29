"""Motor de atualização monetária — mês a mês, determinístico (nunca IA).

5 pilares:
 1. Evolução mensal analítica (tabela linha a linha para laudo).
 2. Linha do tempo de critérios com blindagem anti-anatocismo (juros em balde
    separado — nunca incorporados à base do principal).
 3. Índice customizado (percentuais manuais do perito).
 4. Base de contagem de dias (360 comercial × 365/366 civil) no pró-rata.
 5. Amortização de pagamentos intermediários (3 teses, Art. 354 CC como padrão).
"""
from calendar import monthrange
from datetime import date, datetime

from app.services import indices_bcb
from app.services.calculo_formatacao import formatar_moeda, formatar_percentual


def _norm(d):
    """Converte para date com tolerância — datas vazias/inválidas viram None."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        s = d.strip()[:10]
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None
    return None


def _add_mes(ano: int, mes: int):
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def _fator_dias(d0: date, d1: date, ano: int, mes: int, base_dias: int) -> float:
    """Fração do mês ativa entre d0 e d1 (inclusive), conforme base de dias."""
    ini = max(d0, date(ano, mes, 1))
    fim = min(d1, date(ano, mes, monthrange(ano, mes)[1]))
    dias_ativos = (fim - ini).days + 1
    dias_mes = 30 if base_dias == 360 else monthrange(ano, mes)[1]
    return max(0.0, min(1.0, dias_ativos / dias_mes))


def _pct_do_mes(periodo: dict, ano: int, mes: int, series: dict, customizados: dict) -> float:
    """% de correção do mês conforme o indexador do período."""
    chave = f"{ano:04d}-{mes:02d}"
    indexador = periodo.get("indexador")
    if periodo.get("regime") == "customizado":
        tabela = customizados.get(periodo.get("indice_customizado_nome"), {})
        return float(tabela.get(chave, 0.0))
    if not indexador:
        return 0.0
    return float(series.get(indexador, {}).get(chave, 0.0))


def calcular(valor: float, data_inicial, data_final, timeline: list,
             base_dias: int = 365, pagamentos: list = None,
             tese: str = "juros_primeiro", multa_pct: float = 0.0,
             customizados: dict = None) -> dict:
    valor = float(valor or 0)
    di = _norm(data_inicial)
    if not di:
        # fallback: menor data de início dos períodos
        inicios = [x for x in (_norm(p.get("inicio")) for p in (timeline or [])) if x]
        di = min(inicios) if inicios else None
    if not di:
        raise ValueError("Informe a data inicial do cálculo (ou o termo inicial na decisão).")
    # padrão: último dia do mês anterior (o índice do mês corrente ainda não fechou)
    from datetime import timedelta
    ultimo_mes_fechado = date.today().replace(day=1) - timedelta(days=1)
    df = _norm(data_final) or ultimo_mes_fechado
    if df < di:
        df = ultimo_mes_fechado
    pagamentos = sorted([{"data": _norm(p["data"]) or di, "valor": float(p["valor"])}
                         for p in (pagamentos or []) if p.get("valor")], key=lambda x: x["data"])
    customizados = customizados or {}
    if not timeline:
        raise ValueError("Informe ao menos um período de critério na linha do tempo.")

    # pré-carrega as séries oficiais necessárias
    series = {}
    nao_reconhecidos = []
    for p in timeline:
        idx = p.get("indexador")
        if idx and p.get("regime") != "customizado" and idx not in series:
            try:
                series[idx] = indices_bcb.serie_mensal(idx, di, df)
            except Exception:
                series[idx] = {}
                if idx not in nao_reconhecidos:
                    nao_reconhecidos.append(idx)

    def periodo_do_mes(ano, mes):
        alvo = date(ano, mes, 15)
        for p in timeline:
            pi = _norm(p.get("inicio")) or di
            pf = _norm(p.get("fim")) or df
            if pi <= alvo <= pf:
                return p
        return timeline[-1]

    principal = valor          # principal corrigido (correção compõe — legítimo)
    juros_ac = 0.0             # balde de juros — NUNCA incorporado ao principal
    multa_val = 0.0
    linhas = []
    avisos = []
    for idx in nao_reconhecidos:
        avisos.append(f"Índice '{idx}' não reconhecido — nesse período NÃO houve correção. "
                      f"Use um dos oficiais (IPCA, INPC, IGP-M, IGP-DI, SELIC, TR, Poupança) ou uma tabela customizada.")
    if tese == "principal":
        avisos.append("Tese 'abate no principal' é metodologicamente frágil e contestável (ignora juros vencidos).")

    ano, mes = di.year, di.month
    while (ano, mes) <= (df.year, df.month):
        p = periodo_do_mes(ano, mes)
        frac = _fator_dias(di, df, ano, mes, base_dias)
        nominal_ini = principal

        # correção do mês (índice)
        pct_corr = _pct_do_mes(p, ano, mes, series, customizados)
        principal *= (1 + (pct_corr / 100.0) * frac)

        # juros do mês (simples, sobre o principal corrigido) — salvo regimes que já englobam
        pct_remun = pct_mora = 0.0
        if not (p.get("regime") == "selic" or indices_bcb.engloba_juros(p.get("indexador", ""))):
            pct_remun = float(p.get("juros_remun_am", 0) or 0) * frac
            pct_mora = float(p.get("juros_mora_am", 0) or 0) * frac
            juros_ac += principal * ((pct_remun + pct_mora) / 100.0)

        # pagamentos intermediários deste mês
        for pg in [x for x in pagamentos if x["data"].year == ano and x["data"].month == mes]:
            v = pg["valor"]
            if tese == "principal":
                principal = max(0.0, principal - v)
            elif tese == "proporcional":
                tot = principal + juros_ac
                rj = (juros_ac / tot) if tot > 0 else 0
                juros_ac = max(0.0, juros_ac - v * rj)
                principal = max(0.0, principal - v * (1 - rj))
            else:  # juros_primeiro (Art. 354 CC)
                paga_juros = min(v, juros_ac)
                juros_ac -= paga_juros
                principal = max(0.0, principal - (v - paga_juros))

        linhas.append({
            "mes_ano": f"{mes:02d}/{ano}",
            "valor_nominal": round(nominal_ini, 2),
            "pct_correcao": round(pct_corr * frac, 4),
            "saldo_corrigido": round(principal, 2),
            "pct_juros_remun": round(pct_remun, 4),
            "pct_juros_mora": round(pct_mora, 4),
            "pct_multa": 0.0,
            "saldo_total_mes": round(principal + juros_ac + multa_val, 2),
        })
        ano, mes = _add_mes(ano, mes)

    # multa (uma vez, sobre o principal corrigido final)
    if multa_pct and linhas:
        multa_val = principal * (multa_pct / 100.0)
        linhas[-1]["pct_multa"] = round(multa_pct, 4)
        linhas[-1]["saldo_total_mes"] = round(principal + juros_ac + multa_val, 2)

    # Saída sempre em PT-BR (Global Constraint do plano) — nenhum float cru
    # chega ao front/export; "linhas" acima segue com floats internamente
    # (usados na conta mês a mês), só formatamos na embalagem final.
    linhas_fmt = [{
        "mes_ano": l["mes_ano"],
        "valor_nominal": formatar_moeda(l["valor_nominal"]),
        "pct_correcao": formatar_percentual(l["pct_correcao"]),
        "saldo_corrigido": formatar_moeda(l["saldo_corrigido"]),
        "pct_juros_remun": formatar_percentual(l["pct_juros_remun"]),
        "pct_juros_mora": formatar_percentual(l["pct_juros_mora"]),
        "pct_multa": formatar_percentual(l["pct_multa"]),
        "saldo_total_mes": formatar_moeda(l["saldo_total_mes"]),
    } for l in linhas]

    return {
        "linhas": linhas_fmt,
        "totais": {
            "valor_original": formatar_moeda(round(valor, 2)),
            "principal_corrigido": formatar_moeda(round(principal, 2)),
            "juros": formatar_moeda(round(juros_ac, 2)),
            "multa": formatar_moeda(round(multa_val, 2)),
            "total_pago": formatar_moeda(round(sum(p["valor"] for p in pagamentos), 2)),
            "saldo_final": formatar_moeda(round(principal + juros_ac + multa_val, 2)),
        },
        "avisos": avisos,
        "parametros": {"base_dias": base_dias, "tese": tese, "multa_pct": multa_pct,
                       "data_inicial": di.isoformat(), "data_final": df.isoformat()},
    }
