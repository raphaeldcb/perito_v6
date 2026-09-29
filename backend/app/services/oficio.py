"""Preenchimento de modelos (ofícios/laudos) — mapeia os campos «CAMPO» do
modelo aos dados do processo. Campos não reconhecidos ficam para o usuário
preencher (manual). Novos campos padrão podem ser adicionados aqui ou via
parâmetro 'campos_padrao_extra'.
"""
from datetime import date


def _mes_extenso(m: int) -> str:
    return ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"][m]


def _valor_br(v) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return ""


def valores_do_processo(processo, extras: dict = None) -> dict:
    """Monta o dicionário de campos «CAMPO» → valor a partir do processo.
    Aceita várias grafias do mesmo campo (Nº, NUMERO, PROCESSO...)."""
    hoje = date.today()
    data_ext = f"Campo Grande (MS), {hoje.day} de {_mes_extenso(hoje.month)} de {hoje.year}"
    m = {
        # padrão «CAMPO» (.docx novos)
        "Nº": processo.numero_cnj, "N°": processo.numero_cnj, "NUMERO": processo.numero_cnj,
        "PROCESSO": processo.numero_cnj, "CNJ": processo.numero_cnj,
        "VARA": processo.vara or "", "COMARCA": (processo.vara or "").replace("Vara", "").strip() or "Campo Grande",
        "ESTADO": "MS", "UF": "MS", "CIDADE": "Campo Grande",
        "AUTOR": processo.autor or "", "REQUERENTE": processo.autor or "",
        "REU": processo.reu or "", "REQUERIDO": processo.reu or "",
        "JUIZ": processo.juiz or "", "MAGISTRADO": processo.juiz or "",
        "ESPECIALIDADE": processo.especialidade or "", "AREA": processo.especialidade or "",
        "HONORARIOS": _valor_br(processo.honorarios), "VALOR": _valor_br(processo.honorarios),
        "RESPONSAVEL": getattr(processo, "responsavel", "") or "",
        "DATA": data_ext, "DATA_HOJE": hoje.strftime("%d/%m/%Y"),
        # padrão <CAMPO> (.doc antigos, ofícios DNA)
        "AUTOS": processo.numero_cnj, "VARAS": processo.vara or "",
        "DTRESULT": data_ext, "REQTE": processo.autor or "", "REQDO": processo.reu or "",
    }
    if extras:
        m.update({k.upper(): v for k, v in extras.items()})
    return m


def resolver_campos(campos_modelo: list, valores: dict) -> tuple[dict, list]:
    """Dado os campos do modelo e os valores disponíveis, retorna
    (preenchidos, faltando). Case-insensitive."""
    vmap = {k.upper(): v for k, v in valores.items()}
    preenchidos, faltando = {}, []
    for c in (campos_modelo or []):
        v = vmap.get(c.upper())
        if v not in (None, ""):
            preenchidos[c] = v
        else:
            faltando.append(c)
    return preenchidos, faltando
