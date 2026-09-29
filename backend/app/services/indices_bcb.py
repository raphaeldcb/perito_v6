"""Índices oficiais do Banco Central (API SGS) — persistidos no BD, atualizados a
cada 10 dias pelo worker. O cálculo lê do BD (não depende de rede na hora).
"""
import logging
from datetime import date, datetime, timedelta

import requests

from app.utils import retry, get_circuit_breaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados"

# nome interno -> (código SGS, rótulo, se já engloba juros)
INDICES = {
    "IPCA": (433, "IPCA (IBGE)", False),
    "INPC": (188, "INPC (IBGE)", False),
    "IGPM": (189, "IGP-M (FGV)", False),
    "IGPDI": (190, "IGP-DI (FGV)", False),
    "SELIC": (4390, "SELIC acumulada no mês", True),
    "TR": (7811, "TR — Taxa Referencial (mensal)", False),
    "POUPANCA": (196, "Poupança (nova regra)", True),
}

VALIDADE_DIAS = 10
_mem = {}  # fallback em memória se não houver BD

# apelidos: várias grafias → chave interna (IGP-M, IPCA-E, poupança, taxa selic...)
_ALIAS = {
    "IPCAE": "IPCA", "IPCAESPECIAL": "IPCA",
    "TAXASELIC": "SELIC", "SELICMENSAL": "SELIC",
    "CADERNETADEPOUPANCA": "POUPANCA", "POUPANCANOVA": "POUPANCA",
    "TAXAREFERENCIAL": "TR",
    "IGP": "IGPM",
}


def _normalizar(nome: str) -> str:
    """Uppercase + sem acento + só letras/números. 'IGP-M'→'IGPM', 'poupança'→'POUPANCA'."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode("ascii")
    s = "".join(c for c in s if c.isalnum()).upper()
    if s in INDICES:
        return s
    return _ALIAS.get(s, s)


def _parse_serie(itens) -> dict:
    saida = {}
    for item in itens:
        try:
            dt = datetime.strptime(item["data"], "%d/%m/%Y").date()
            saida[f"{dt.year:04d}-{dt.month:02d}"] = float(item["valor"])
        except (KeyError, ValueError):
            continue
    return saida


def _fetch_bcb(cod: int) -> dict:
    """Baixa a série mensal da API do BCB. Se o período longo for rejeitado
    (algumas séries, como a TR=226, dão 406), usa ?ultimos=420 (35 anos)."""
    url = BCB_URL.format(cod=cod)
    try:
        resp = requests.get(url, params={"formato": "json", "dataInicial": "01/01/1994",
                                         "dataFinal": date.today().strftime("%d/%m/%Y")}, timeout=40)
        resp.raise_for_status()
        return _parse_serie(resp.json())
    except Exception:
        resp = requests.get(url, params={"formato": "json", "ultimos": 420}, timeout=40)
        resp.raise_for_status()
        return _parse_serie(resp.json())


def atualizar_todos(db, forcar: bool = False) -> int:
    """Atualiza no BD as séries vencidas (>10 dias). Chamado pelo worker."""
    from app.models import IndiceCache
    atualizados = 0
    limite = datetime.utcnow() - timedelta(days=VALIDADE_DIAS)
    for nome, (cod, _r, _e) in INDICES.items():
        reg = db.query(IndiceCache).filter(IndiceCache.indexador == nome).first()
        if not forcar and reg and reg.atualizado_em and reg.atualizado_em > limite:
            continue
        try:
            valores = _fetch_bcb(cod)
        except Exception as e:
            logger.warning(f"BCB {nome}: {e}")
            continue
        if not valores:
            continue
        if reg:
            reg.valores = valores
            reg.atualizado_em = datetime.utcnow()
        else:
            db.add(IndiceCache(indexador=nome, valores=valores, atualizado_em=datetime.utcnow()))
        _mem[nome] = valores
        atualizados += 1
    db.commit()
    if atualizados:
        logger.info(f"📈 {atualizados} índices do BCB atualizados")
    return atualizados


def _serie_do_bd(nome: str) -> dict:
    """Lê a série do BD; se não houver/vencida, busca no BCB na hora e grava."""
    if nome in _mem:
        return _mem[nome]
    from app.services.database import SessionLocal
    from app.models import IndiceCache
    db = SessionLocal()
    reg = None
    try:
        reg = db.query(IndiceCache).filter(IndiceCache.indexador == nome).first()
        limite = datetime.utcnow() - timedelta(days=VALIDADE_DIAS)
        if reg and reg.valores and reg.atualizado_em and reg.atualizado_em > limite:
            _mem[nome] = reg.valores
            return reg.valores
        # vencido ou inexistente → busca agora
        cod = INDICES[nome][0]
        valores = _fetch_bcb(cod)
        if reg:
            reg.valores = valores; reg.atualizado_em = datetime.utcnow()
        else:
            db.add(IndiceCache(indexador=nome, valores=valores, atualizado_em=datetime.utcnow()))
        db.commit()
        _mem[nome] = valores
        return valores
    except Exception as e:
        logger.warning(f"serie {nome}: {e}")
        return (reg.valores if reg and reg.valores else {})
    finally:
        db.close()


def serie_mensal(indexador: str, data_ini=None, data_fim=None) -> dict:
    """Retorna {"AAAA-MM": pct} do indexador (do BD, atualizado a cada 10 dias).
    Aceita várias grafias (IGP-M, IPCA-E, poupança...) via normalização."""
    nome = _normalizar(indexador)
    if nome not in INDICES:
        raise ValueError(f"Indexador desconhecido: {indexador}")
    return _serie_do_bd(nome)


def engloba_juros(indexador: str) -> bool:
    return INDICES.get(_normalizar(indexador), (0, "", False))[2]


def listar() -> list[dict]:
    return [{"codigo": k, "rotulo": v[1], "engloba_juros": v[2]} for k, v in INDICES.items()]
