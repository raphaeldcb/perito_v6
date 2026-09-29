"""
Formatação PT-BR reutilizável para o módulo de Cálculo (Ferramenta de Cálculo V2).

Global Constraint do plano: TODAS as saídas numéricas do módulo de cálculo
devem sair em PT-BR — separador de milhar='.', decimal=','.
"""
from decimal import Decimal, ROUND_HALF_UP


def formatar_pt_br(valor: float | None, decimais: int = 2) -> str:
    """Formata número em PT-BR: 1234567.89 -> '1.234.567,89'"""
    if valor is None:
        return ""

    dec = Decimal(str(valor)).quantize(Decimal(10) ** -decimais, rounding=ROUND_HALF_UP)
    negativo = dec < 0
    dec = abs(dec)

    inteiro, frac = f"{dec:f}".split(".") if decimais > 0 else (f"{dec:f}", "")

    partes = []
    for i, char in enumerate(reversed(inteiro)):
        if i > 0 and i % 3 == 0:
            partes.append(".")
        partes.append(char)
    inteiro_fmt = "".join(reversed(partes))

    sinal = "-" if negativo else ""
    if decimais > 0:
        return f"{sinal}{inteiro_fmt},{frac}"
    return f"{sinal}{inteiro_fmt}"


def formatar_percentual(valor: float, decimais: int = 2) -> str:
    """Formata percentual: 0.5 -> '0,50%' (valor já em base 100, ex: 0.5 = 0,5%)"""
    return f"{formatar_pt_br(valor, decimais)}%"


def formatar_moeda(valor: float, decimais: int = 2) -> str:
    """Formata moeda: 1234567.89 -> 'R$ 1.234.567,89'"""
    return f"R$ {formatar_pt_br(valor, decimais)}"
