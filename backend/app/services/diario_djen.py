"""Diário de Justiça Eletrônico Nacional (DJEN) — API pública Comunica (CNJ).

Monitoramento para PERÍCIA: o perito é NOMEADO no corpo das decisões, não
intimado por OAB. Então busca por TERMOS a incluir (nome do escritório/peritos/
especialidades) via busca de texto livre, filtra os termos a excluir, e as
publicações encontradas são salvas para o Qwen analisar (nomeação, prazo, honorários).
Extensível: basta acrescentar a sigla do tribunal.

Inclui retry + circuit breaker para resiliência.
"""
import logging
from datetime import date, timedelta

import requests

from app.utils import retry, get_circuit_breaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)

DJEN_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
UA = {"User-Agent": "Mozilla/5.0 (PeritoSystem)"}

TRIBUNAIS_PADRAO = ["TJMS", "TJMT", "TJAC", "TJAM", "TJRO", "TJTO"]

# Circuit breaker para DJEN
_djen_breaker = get_circuit_breaker("djen", threshold=5, timeout=60)


def _config(db):
    from app.models import DiarioConfig
    cfg = db.query(DiarioConfig).filter(DiarioConfig.id == 1).first()
    if not cfg:
        cfg = DiarioConfig(id=1, incluir=[], excluir=[], tribunais=TRIBUNAIS_PADRAO)
        db.add(cfg); db.commit(); db.refresh(cfg)
    return cfg


@retry(max_attempts=3, backoff=1.5, initial_delay=1.0)
def _buscar_termo_interno(
    sigla: str, termo: str, di: str, df: str, itens: int = 50
) -> list[dict]:
    """Implementação interna com retry automático."""
    params = {
        "siglaTribunal": sigla,
        "texto": termo,
        "itensPorPagina": itens,
        "pagina": 1,
        "dataDisponibilizacaoInicio": di,
        "dataDisponibilizacaoFim": df,
    }
    r = requests.get(DJEN_URL, params=params, headers=UA, timeout=30)
    if r.status_code == 429:
        # Rate limit; o retry vai esperar e tentar novamente
        logger.warning(f"DJEN {sigla}/{termo}: rate limit (429)")
    r.raise_for_status()
    return r.json().get("items") or []


def _buscar_termo(sigla: str, termo: str, di: str, df: str, itens: int = 50) -> list[dict]:
    """Busca termo no DJEN com retry + circuit breaker.

    Retorna lista vazia em caso de falha (fallback seguro).
    """
    try:
        itens_j = _djen_breaker.call_function(
            _buscar_termo_interno, sigla, termo, di, df, itens
        )
    except CircuitBreakerOpen as e:
        logger.error(f"Circuit breaker DJEN OPEN: {e}")
        return []
    except Exception as e:
        logger.warning(f"DJEN {sigla}/{termo}: {e}")
        return []

    out = []
    for it in itens_j:
        out.append({
            "id": it.get("id"),
            "tribunal": it.get("siglaTribunal"),
            "numero_processo": it.get("numero_processo"),
            "tipo": it.get("tipoComunicacao"),
            "orgao": it.get("nomeOrgao"),
            "classe": it.get("nomeClasse"),
            "data": it.get("data_disponibilizacao"),
            "texto": (it.get("texto") or "")[:4000],
            "link": it.get("link"),
            "termo": termo,
        })
    return out


def consultar(tribunais: list[str], incluir: list[str], excluir: list[str] = None,
              dias: int = 7) -> list[dict]:
    """Busca cada termo de inclusão nos tribunais e remove os que batem em exclusão."""
    excluir = [e.lower() for e in (excluir or []) if e.strip()]
    incluir = [i for i in (incluir or []) if i.strip()]
    if not incluir:
        return []
    df = date.today().isoformat()
    di = (date.today() - timedelta(days=dias)).isoformat()
    import time
    vistos, resultado = set(), []
    for sigla in (tribunais or TRIBUNAIS_PADRAO):
        for termo in incluir:
            time.sleep(0.4)  # espaça as chamadas p/ não tomar 429 do DJEN
            for pub in _buscar_termo(sigla, termo, di, df):
                if pub["id"] in vistos:
                    continue
                txt = (pub.get("texto") or "").lower()
                if any(x in txt for x in excluir):
                    continue
                vistos.add(pub["id"])
                resultado.append(pub)
    resultado.sort(key=lambda x: x.get("data") or "", reverse=True)
    return resultado


def consultar_e_salvar(db) -> int:
    """Automação: usa a config salva, salva publicações novas como intimação
    (status 'pendente' → o worker analise_qwen extrai nomeação/prazo/honorários)."""
    from app.models import Processo, Intimacao
    cfg = _config(db)
    if not cfg.incluir:
        return 0  # sem termos configurados, não faz nada
    pubs = consultar(cfg.tribunais or TRIBUNAIS_PADRAO, cfg.incluir, cfg.excluir, dias=3)
    novas = 0
    for p in pubs:
        ext = f"djen:{p['id']}"
        if db.query(Intimacao).filter(Intimacao.external_id == ext).first():
            continue
        cnj = p.get("numero_processo")
        if not cnj:
            continue
        proc = db.query(Processo).filter(Processo.numero_cnj == cnj).first()
        if not proc:
            proc = Processo(numero_cnj=cnj, titulo=f"Processo {cnj}",
                            tribunal=p.get("tribunal"), status="ativo", source_system="djen")
            db.add(proc); db.flush()
        db.add(Intimacao(
            processo_id=proc.id, origem="djen", tipo=p.get("tipo"),
            assunto=(p.get("classe") or p.get("tipo") or "Publicação"),
            conteudo=p.get("texto"), status="pendente", external_id=ext,
            source_system="djen", pdf_path=p.get("link"),
        ))
        novas += 1
    db.commit()
    if novas:
        logger.info(f"📰 DJEN: {novas} publicações novas (para análise Qwen)")
    return novas


def captar_automatico(db, limite: int = 12) -> int:
    """Captação automática: busca com a config e ENFILEIRA a análise do Qwen
    (job analisar_captacao) das publicações NOVAS — dedup por djen_id na tabela
    Oportunidade. NÃO cria Processo (captação gera lead/Oportunidade ranqueada,
    não caso seu). Cap de `limite` por ciclo (Qwen é lento). Retorna quantas enfileirou."""
    from app.models import Oportunidade, Job
    cfg = _config(db)
    if not cfg.incluir:
        return 0
    # trava anti-empilhamento: só enfileira se não houver captação em andamento
    # (senão o worker re-enfileira as mesmas pubs antes das Oportunidades existirem)
    em_andamento = db.query(Job).filter(
        Job.tipo == "analisar_captacao", Job.status.in_(["na_fila", "processando"])).first()
    if em_andamento:
        return 0
    pubs = consultar(cfg.tribunais or TRIBUNAIS_PADRAO, cfg.incluir, cfg.excluir, dias=3)
    ja = {str(x[0]) for x in db.query(Oportunidade.djen_id).all() if x[0]}
    novas = [p for p in pubs if str(p.get("id")) not in ja][:limite]
    if not novas:
        return 0
    db.add(Job(tipo="analisar_captacao", status="na_fila", payload={"publicacoes": novas}))
    db.commit()
    logger.info(f"🎯 Captação DJEN: {len(novas)} publicações novas enfileiradas p/ Qwen")
    return len(novas)
