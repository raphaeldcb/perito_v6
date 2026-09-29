"""
Formatador de intimações — converte JSON da análise Qwen em MD/TXT legível.
Gera tabela resumida e documento markdown estruturado.
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def formatar_resultado(analise: dict, texto_original: str = "", numero_cnj: str = "") -> str:
    """
    Formata análise Qwen em Markdown estruturado.

    Args:
        analise: dict com {numero_processo, tipo, prazo_dias, juiz, vara, partes, quesitos, urgencia, resumo}
        texto_original: texto extraído do PDF (opcional, para referência)
        numero_cnj: número CNJ (opcional, override)

    Returns:
        string markdown formatada
    """
    numero = numero_cnj or analise.get("numero_processo", "?")
    tipo = analise.get("tipo", "?")
    prazo = analise.get("prazo_dias", "?")
    juiz = analise.get("juiz", "?")
    vara = analise.get("vara", "?")
    urgencia = analise.get("urgencia", "?").upper()
    resumo = analise.get("resumo", "")
    partes = analise.get("partes", [])
    quesitos = analise.get("quesitos", [])

    # Mapa de urgência → emoji
    urgencia_map = {"ALTA": "🔴", "MEDIA": "🟡", "BAIXA": "🟢"}
    icon = urgencia_map.get(urgencia, "⚪")

    # Montar markdown
    md = f"""# {icon} Intimação: {numero}

## Informações Básicas

| Campo | Valor |
|-------|-------|
| **Número CNJ** | {numero} |
| **Tipo** | {tipo} |
| **Juiz** | {juiz} |
| **Vara** | {vara} |
| **Prazo** | {prazo} dias |
| **Urgência** | {icon} {urgencia} |

## Resumo

{resumo}

"""

    # Partes
    if partes:
        md += "## Partes\n\n"
        for parte in partes:
            md += f"- {parte}\n"
        md += "\n"

    # Quesitos
    if quesitos:
        md += "## Quesitos a Responder\n\n"
        for i, quesito in enumerate(quesitos, 1):
            md += f"{i}. {quesito}\n"
        md += "\n"

    # Rodapé
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md += f"""---

**Data de processamento:** {agora}
**Fonte:** Email ipcms@ipcms.com.br
**Status:** Pendente análise pericial

"""

    return md


def formatar_tabela_resumo(intimacoes_list: list) -> str:
    """
    Formata lista de intimações em tabela Markdown compacta.

    Args:
        intimacoes_list: lista de dicts com análises

    Returns:
        tabela markdown
    """
    tabela = """| CNJ | Juiz | Vara | Prazo (dias) | Urgência | Resumo |
|-----|------|------|--------|----------|--------|
"""

    for intim in intimacoes_list:
        num = intim.get("numero_processo", "?")[:20]
        juiz = intim.get("juiz", "?")[:15]
        vara = intim.get("vara", "?")[:15]
        prazo = intim.get("prazo_dias", "?")
        urgencia = intim.get("urgencia", "?").upper()[0]  # Primeira letra
        resumo = intim.get("resumo", "")[:60].replace("\n", " ")

        urgencia_icon = {"A": "🔴", "M": "🟡", "B": "🟢"}.get(urgencia, "⚪")

        tabela += f"| {num} | {juiz} | {vara} | {prazo} | {urgencia_icon} | {resumo}... |\n"

    return tabela


def salvar_markdown(conteudo: str, caminho: str) -> None:
    """Salva markdown em arquivo."""
    import os
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    logger.info(f"✅ Markdown salvo: {caminho}")


def salvar_json(dados: dict, caminho: str) -> None:
    """Salva JSON formatado em arquivo."""
    import os
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    logger.info(f"✅ JSON salvo: {caminho}")
