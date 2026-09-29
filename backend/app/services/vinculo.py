"""Vínculo intimação → processo: propaga o que o Qwen extraiu (partes, vara, juiz)
para o cadastro do processo. Só preenche campos VAZIOS — nunca sobrescreve edição
manual. Reutilizável no intake (job analise_ia) e no re-sync de sistemas legados.
"""
import logging

logger = logging.getLogger(__name__)

AUTOR_KW = ("autor", "exequente", "requerente", "reclamante", "impetrante",
            "embargante", "credor", "agravante", "apelante", "recorrente")
REU_KW = ("reu", "réu", "executado", "requerido", "reclamado", "impetrado",
          "embargado", "devedor", "agravado", "apelado", "recorrido")


def classificar_partes(partes):
    """Dado o array de partes do Qwen, devolve (autor, reu) como nomes.
    Tolera {nome: papel, tipo: nome} e {papel, nome, doc}."""
    autor = reu = None
    for p in (partes or []):
        if not isinstance(p, dict):
            continue
        vals = [str(v).strip() for v in p.values() if v and str(v).strip()]
        if not vals:
            continue
        papel = next((v for v in vals if any(k in v.lower() for k in AUTOR_KW + REU_KW)), "")
        nome = next((v for v in vals if v != papel), papel)
        pl = papel.lower()
        if any(k in pl for k in AUTOR_KW) and not autor:
            autor = nome
        elif any(k in pl for k in REU_KW) and not reu:
            reu = nome
    return autor, reu


def propagar(processo, dados: dict) -> bool:
    """Preenche campos vazios do processo a partir de dados_estruturados.
    Retorna True se mudou algo."""
    if not processo or not dados:
        return False
    mudou = False
    autor, reu = classificar_partes(dados.get("partes"))

    def preenche(attr, valor, limite):
        nonlocal mudou
        if valor and not getattr(processo, attr, None):
            setattr(processo, attr, str(valor)[:limite])
            mudou = True

    preenche("autor", autor, 200)
    preenche("reu", reu, 200)
    preenche("vara", dados.get("vara"), 100)
    preenche("juiz", dados.get("juiz"), 200)
    # título melhor que "Processo <cnj>"
    if (not processo.titulo or str(processo.titulo).startswith("Processo ")) and (autor or reu):
        processo.titulo = f"{autor or '?'} × {reu or '?'}"[:200]
        mudou = True
    # classe/assunto (ex: "Cumprimento de sentença") no descricao, se vazio
    preenche("descricao", dados.get("tipo"), 2000)
    return mudou
