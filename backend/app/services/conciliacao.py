"""Conciliação bancária: casa o favorecido de um lançamento com um coletador
ou usuário, por similaridade de nome/apelido.

Ex.: extrato mostra "PIX ENVIADO GERIEL SOUZA" → casa com o coletador cujo
apelido/nome contém "geriel". Score alto = automático; baixo = sugestão para
conferência manual.
"""
import re
import unicodedata
from difflib import SequenceMatcher


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9 ]", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


# Ruído comum em descrições de extrato que não faz parte do nome do favorecido
STOPWORDS = {
    "pix", "enviado", "recebido", "ted", "doc", "transferencia", "transf",
    "pagamento", "pagto", "para", "de", "da", "do", "ltda", "me", "epp",
    "cpf", "cnpj", "banco", "conta", "credito", "debito", "boleto", "favorecido",
}


def _tokens_nome(texto: str) -> set:
    return {t for t in normalizar(texto).split() if t not in STOPWORDS and len(t) > 2}


# Sobrenomes muito comuns: sozinhos não confirmam um match (evita casar
# "Pablo Silva de Oliveira" com "Marta Silva de Oliveira" só pelos sobrenomes).
SOBRENOMES_COMUNS = {
    "silva", "souza", "sousa", "santos", "oliveira", "pereira", "lima",
    "ferreira", "rodrigues", "almeida", "costa", "gomes", "ribeiro",
    "carvalho", "dias", "nunes", "araujo", "fernandes", "vieira", "barros",
}


def score_nome(favorecido: str, alvo_nome: str, alvo_apelido: str = "") -> float:
    """0..1 — quão bem o favorecido do extrato bate com o nome/alvo.

    Rigoroso de propósito: só dá score alto quando a MAIORIA dos tokens de
    nome coincide (Dice), nunca por um único primeiro nome. Um comprovante no
    coletador errado é pior que um pendente para conferência manual.
    """
    fav = normalizar(favorecido)
    if not fav:
        return 0.0
    tf = _tokens_nome(favorecido)
    if not tf:
        return 0.0

    melhor = 0.0

    # 1) Match por nome completo (Dice sobre tokens)
    tn = _tokens_nome(alvo_nome)
    if tn:
        inter = tf & tn
        n_inter = len(inter)
        distintivos = inter - SOBRENOMES_COMUNS  # tokens fortes (não sobrenome comum)
        dice = (2 * n_inter) / (len(tf) + len(tn))
        # exige pelo menos 2 tokens coincidentes E ao menos 1 token distintivo
        if n_inter >= 2 and distintivos:
            melhor = max(melhor, min(0.99, dice))
        else:
            melhor = max(melhor, dice * 0.5)  # fraco → vira sugestão pendente

    # Obs.: NÃO casamos por apelido/primeiro nome isolado. Nesta base os
    # apelidos são o próprio primeiro nome (Rogério, Antônio, Maria...) e
    # casariam com qualquer homônimo. O match por nome completo acima já
    # resolve os casos legítimos (ex: "GERIEL SOUZA" → coletador Geriel Souza).
    return round(melhor, 3)


def conciliar_lancamento(favorecido: str, coletadores: list, usuarios: list,
                         limiar: float = 0.66):
    """Retorna (tipo, id, score) do melhor match acima do limiar, ou (None, None, best).

    coletadores: lista de (id, nome, apelido); usuarios: lista de (id, nome).
    """
    melhor_tipo, melhor_id, melhor_score = None, None, 0.0

    for cid, nome, apelido in coletadores:
        s = score_nome(favorecido, nome, apelido or "")
        if s > melhor_score:
            melhor_tipo, melhor_id, melhor_score = "coletador", cid, s

    for uid, nome in usuarios:
        s = score_nome(favorecido, nome)
        if s > melhor_score:
            melhor_tipo, melhor_id, melhor_score = "usuario", uid, s

    if melhor_score >= limiar:
        return melhor_tipo, melhor_id, melhor_score
    # abaixo do limiar: devolve a melhor sugestão mas sem casar automaticamente
    return None, None, melhor_score
