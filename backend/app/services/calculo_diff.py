"""Diff visual entre duas versões de um cálculo (Task 6 do plano
docs/superpowers/plans/2026_001-ferramenta_calculo_v2.md).

Puramente numérico — quem extrai o float do JSON de resultado (que pode vir
formatado em PT-BR, ver Task 2/`_saldo_final_numerico` em routes/calculo.py)
é responsabilidade de quem chama.
"""


def calcular_diff(saldo_v1: float, saldo_v2: float) -> dict:
    """Calcula a diferença entre duas versões de um cálculo."""
    delta_abs = saldo_v2 - saldo_v1
    delta_pct = (delta_abs / saldo_v1 * 100) if saldo_v1 != 0 else 0

    return {
        "saldo_anterior": saldo_v1,
        "saldo_novo": saldo_v2,
        "delta_absoluto": delta_abs,
        "delta_pct": delta_pct,
        "maior_que_10_pct": abs(delta_pct) > 10,
    }
