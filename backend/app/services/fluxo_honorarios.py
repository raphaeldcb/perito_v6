"""Motor de honorários — a lógica do fluxo de ofícios do IPC.

Ciclo: intimação → PROPOSTA (nº 01) → protocolo → nova intimação (impugnação /
pagamento ao final) → DECIDE por histórico do juiz + % de redução:
  - reduziu >= LIMIAR (10%)  OU  juízo "nunca paga"  → DECLINA (ofício sequencial)
  - redução pequena / juízo que paga                 → RATIFICA (sustenta o valor)
O NN (nº do ofício no mesmo caso) = quantos ofícios já emitimos + 1.
"""
import re
import unicodedata
from decimal import Decimal

from app.models import Oficio
from app.models.fluxo_honorarios import HistoricoJuiz

LIMIAR_REDUCAO = Decimal("0.10")  # >=10% de corte => declina

# templates canônicos (MODELOS_TEMPLATE) por situação
TEMPLATE = {
    "proposta": "9 - PROPOSTA JUDICIAL - PEDE MAJORAÇÃO AO FINAL.docx",
    "ratifica": "OF padrão ratifica honorários.docx",
    "declina": "OF241599-47 DECLINA AO FINAL.docx",
}


def _slug(nome: str) -> str:
    if not nome:
        return ""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _slug_juizo(comarca, vara) -> str:
    """Chave estável do JUÍZO = comarca + vara (o nome do juiz costuma faltar/rotacionar)."""
    return _slug(f"{comarca or ''}|{vara or ''}").strip("-")


def historico_juizo(db, comarca, vara):
    slug = _slug_juizo(comarca, vara)
    if not slug:
        return None
    return db.query(HistoricoJuiz).filter(HistoricoJuiz.juiz_slug == slug).first()


def proximo_nn(db, processo_id: int) -> int:
    """NN sequencial: quantos ofícios já emitimos nesse caso + 1 (01 = proposta)."""
    ja = db.query(Oficio).filter(Oficio.processo_id == processo_id).count()
    return ja + 1


def decidir_honorarios(db, processo_id: int, juiz_nome: str,
                       situacao: str, valor_proposto=None, valor_arbitrado=None) -> dict:
    """Decide a ação e qual template usar.

    situacao: 'proposta' (nomeação nova) | 'impugnacao' (impugnaram os honorários)
              | 'pagamento_ao_final' (condicionaram pagamento ao final pela sucumbente)
    Retorna: {acao, template, motivo, reducao_pct, nn, juiz_conhecido, nunca_paga}
    """
    from app.models import Processo
    nn = proximo_nn(db, processo_id)
    proc = db.query(Processo).get(processo_id) if processo_id else None
    hist = historico_juizo(db, proc.comarca if proc else None, proc.vara if proc else None)
    nunca_paga = bool(hist and hist.nunca_paga)
    base = {"nn": nn, "juiz_conhecido": hist is not None, "nunca_paga": nunca_paga,
            "reducao_pct": None}

    if situacao == "proposta":
        return {**base, "acao": "proposta", "template": TEMPLATE["proposta"],
                "motivo": "Nomeação nova — proposta de honorários com pedido de majoração."}

    if situacao == "pagamento_ao_final":
        return {**base, "acao": "declina", "template": TEMPLATE["declina"],
                "motivo": "Pagamento condicionado ao final pela sucumbente — insegurança de "
                          "recebimento (reduções em instância superior sem notificação). Declina."}

    # impugnação de honorários
    reducao = None
    if valor_proposto and valor_arbitrado:
        vp, va = Decimal(str(valor_proposto)), Decimal(str(valor_arbitrado))
        if vp > 0:
            reducao = (vp - va) / vp  # fração; 0.16 = 16%
    base["reducao_pct"] = float(round(reducao * 100, 2)) if reducao is not None else None

    if nunca_paga:
        return {**base, "acao": "declina", "template": TEMPLATE["declina"],
                "motivo": f"Juízo com histórico de não pagar/homologar ({hist.declinamos or 0} "
                          f"declínios). Declina."}
    if reducao is not None and reducao >= LIMIAR_REDUCAO:
        return {**base, "acao": "declina", "template": TEMPLATE["declina"],
                "motivo": f"Redução de {base['reducao_pct']}% (≥10%) inviabiliza o trabalho. Declina."}
    return {**base, "acao": "ratifica", "template": TEMPLATE["ratifica"],
            "motivo": "Redução abaixo de 10% (ou não informada) — ratifica e sustenta os honorários."}


def registrar_atuacao(db, juiz_nome: str, comarca: str = None, vara: str = None,
                      reduziu: bool = False, reducao_pct=None, homologou: bool = False,
                      declinamos: bool = False):
    """Acumula o comportamento do juízo (constrói o histórico ao longo do tempo)."""
    slug = _slug_juizo(comarca, vara) or _slug(juiz_nome)
    if not slug:
        return None
    h = db.query(HistoricoJuiz).filter(HistoricoJuiz.juiz_slug == slug).first()
    if not h:
        h = HistoricoJuiz(juiz_slug=slug, juiz_nome=juiz_nome or f"{vara}, {comarca}",
                          comarca=comarca, vara=vara,
                          total_atuacoes=0, homologou=0, reduziu=0, declinamos=0)
        db.add(h)
    h.total_atuacoes = (h.total_atuacoes or 0) + 1
    if homologou:
        h.homologou = (h.homologou or 0) + 1
    if declinamos:
        h.declinamos = (h.declinamos or 0) + 1
    if reduziu:
        n_ant = h.reduziu or 0
        h.reduziu = n_ant + 1
        if reducao_pct is not None:
            media_ant = Decimal(str(h.reducao_media_pct or 0))
            h.reducao_media_pct = (media_ant * n_ant + Decimal(str(reducao_pct))) / (n_ant + 1)
    db.commit()
    return h
