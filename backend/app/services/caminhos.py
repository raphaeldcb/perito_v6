"""Tradução inteligente de caminhos Windows ↔ Mac/Linux.

O admin pode colar um caminho do Windows (I:\\MODELOS\\DNA) mesmo com o
sistema rodando em Mac/VPS: o valor original é preservado, e a resolução
converte separadores e aplica o mapa de unidades (parâmetro
'mapa_unidades_windows', JSON tipo {"I:": "/Users/.../MODELOS"}).
Nada quebra por causa do estilo do caminho — no máximo fica marcado
como 'não encontrado neste servidor'.
"""
import json
import os
import re

WINDOWS_RE = re.compile(r"^[A-Za-z]:[\\/]")
UNC_RE = re.compile(r"^\\\\")  # \\servidor\pasta


def analisar_caminho(valor: str, mapa_unidades: dict | None = None) -> dict:
    """Retorna {original, estilo, resolvido, existe_aqui, observacao}."""
    valor = (valor or "").strip()
    mapa = mapa_unidades or {}
    resultado = {
        "original": valor,
        "estilo": "vazio",
        "resolvido": valor,
        "existe_aqui": False,
        "observacao": "",
    }
    if not valor:
        return resultado

    if WINDOWS_RE.match(valor):
        resultado["estilo"] = "windows"
        unidade = valor[:2].upper()  # ex: "I:"
        resto = valor[2:].replace("\\", "/").lstrip("/")
        raiz = (mapa.get(unidade) or "").rstrip("/")
        if raiz:
            resultado["resolvido"] = f"{raiz}/{resto}"
            resultado["observacao"] = f"unidade {unidade} mapeada para {raiz}"
        else:
            resultado["resolvido"] = f"/{resto}"
            resultado["observacao"] = (
                f"unidade {unidade} sem mapeamento — defina em "
                "'mapa_unidades_windows' (categoria sistema)"
            )
    elif UNC_RE.match(valor):
        resultado["estilo"] = "unc"
        resultado["resolvido"] = "/Volumes/" + valor.lstrip("\\").replace("\\", "/")
        resultado["observacao"] = "caminho de rede Windows — no Mac montado em /Volumes"
    else:
        resultado["estilo"] = "posix"
        resultado["resolvido"] = valor.replace("\\", "/")

    resultado["existe_aqui"] = os.path.exists(resultado["resolvido"])
    if not resultado["existe_aqui"] and resultado["resolvido"].startswith("/Users/"):
        resultado["observacao"] = (resultado["observacao"] + " · " if resultado["observacao"] else "") + \
            "caminho do Mac — verificado pelo agente, não pelo servidor"
    return resultado


def carregar_mapa(valor_json: str) -> dict:
    try:
        mapa = json.loads(valor_json or "{}")
        return {str(k).upper().rstrip(":") + ":": str(v) for k, v in mapa.items()}
    except (json.JSONDecodeError, AttributeError):
        return {}
