"""Job: lê o PDF da decisão judicial oficial de um processo e usa o Qwen
(Ollama local) para sugerir as datas dos marcos processuais tokenizados na
regra semântica de um padrão de cálculo. Task 8 do plano
docs/superpowers/plans/2026_001-ferramenta_calculo_v2.md.

Fluxo: POST /api/v1/calculo/aplicar-padrao cria o Job e dispara este handler
via BackgroundTasks (não pela fila de polling do agente Windows/Mac —
diferente de protocolo/eSAJ, aqui o Qwen é alcançável direto via HTTP, ver
app/jobs/__init__.py). O resultado nunca é uma data "chutada": se o PDF não
existe, a regra não tem token ou o Qwen não devolve JSON, o job termina em
erro explícito — nunca inventa uma sugestão pra não deixar a fila "vazia"
(regra global do plano: padrões semânticos sempre validam contra o
documento oficial, nunca um relatório de parte, e nunca fake em produção).
"""
import json
import logging
import os
from pathlib import Path

import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CalculoArvoreDecisao, Job, PadraoCalculo, Processo
from app.services.padroes_semanticos import tokenizar_regra

logger = logging.getLogger(__name__)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "perito-qwen")
MAX_CHARS_DECISAO = 4000

PROMPT_TEMPLATE = """Você é um assistente jurídico. Leia a decisão judicial abaixo e extraia as seguintes datas: {tokens}.

Para cada data, identifique:
1. A data exata (formato YYYY-MM-DD)
2. O contexto/trecho da decisão que justifica

Se não encontrar uma data, use null.

DECISÃO:
{texto}

Responda APENAS com um JSON, sem nenhum texto antes ou depois, no formato:
{{"datas": {{"TOKEN": "YYYY-MM-DD ou null", ...}}, "contextos": {{"TOKEN": "trecho..."}}}}"""


class InterpretacaoError(Exception):
    """Falha esperada (PDF ausente, sem tokens, Qwen indisponível/inválido) —
    sempre tratada, nunca deixa o job "sumir" em processando."""


def _extrair_texto_pdf(pdf_path: str) -> str:
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        return "".join(pagina.extract_text() or "" for pagina in pdf.pages)


def _chamar_qwen(prompt: str) -> str:
    """Chama o Qwen via Ollama local (mesmo endpoint/protocolo usado em
    laudo_generator.py e laudo_qwen.py)."""
    resp = requests.post(
        f"{settings.ollama_url}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return (resp.json().get("response") or "").strip()


def _parse_datas_sugeridas(resposta: str) -> dict:
    """Qwen às vezes cerca o JSON com texto solto — extrai só o bloco {...}."""
    inicio, fim = resposta.find("{"), resposta.rfind("}")
    if inicio == -1 or fim == -1:
        raise InterpretacaoError(f"Resposta do Qwen sem JSON: {resposta[:300]!r}")
    bloco = json.loads(resposta[inicio:fim + 1])
    return bloco.get("datas", {})


def executar_interpretar_decisao(job_id: int, padrao_id: int, processo_id: int, db: Session) -> dict:
    """Executa o job de ponta a ponta e persiste em CalculoArvoreDecisao.

    Sempre atualiza `job.status`/`job.erro`/`job.resultado` quando `job_id`
    corresponde a um Job real (idempotente: chamável direto em teste sem Job
    também, retorna {"erro": ...} sem tentar gravar em Job inexistente).
    """
    job = db.query(Job).filter(Job.id == job_id).first()

    def _falhar(mensagem: str) -> dict:
        logger.error(f"[interpretar_decisao_oficial] job={job_id}: {mensagem}")
        if job:
            job.status = "erro"
            job.erro = mensagem[:2000]
            db.commit()
        return {"erro": mensagem}

    padrao = db.query(PadraoCalculo).filter(PadraoCalculo.id == padrao_id).first()
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not padrao or not processo:
        return _falhar("Padrão ou processo não encontrado")

    if not padrao.regra_semantica:
        return _falhar("Padrão não tem regra_semantica configurada")

    tokens = tokenizar_regra(padrao.regra_semantica)
    if not tokens:
        return _falhar("Regra semântica não contém tokens [MARCO] para extrair")

    pdf_path = processo.decisao_oficial_path
    if not pdf_path or not Path(pdf_path).exists():
        return _falhar("PDF da decisão oficial não encontrado (processo.decisao_oficial_path)")

    try:
        texto_completo = _extrair_texto_pdf(pdf_path)
    except Exception as e:
        return _falhar(f"Erro ao ler PDF: {e}")

    prompt = PROMPT_TEMPLATE.format(
        tokens=", ".join(tokens),
        texto=texto_completo[:MAX_CHARS_DECISAO],
    )

    try:
        resposta = _chamar_qwen(prompt)
    except Exception as e:
        return _falhar(f"Erro ao chamar Qwen: {e}")

    try:
        datas_sugeridas = _parse_datas_sugeridas(resposta)
    except InterpretacaoError as e:
        return _falhar(str(e))

    arvore = db.query(CalculoArvoreDecisao).filter(
        CalculoArvoreDecisao.padrao_id == padrao_id,
        CalculoArvoreDecisao.processo_id == processo_id,
    ).first()
    if arvore:
        arvore.regra_original = padrao.regra_semantica
        arvore.datas_sugeridas = datas_sugeridas
        arvore.ai_interpretacao_texto = resposta
    else:
        arvore = CalculoArvoreDecisao(
            padrao_id=padrao_id,
            processo_id=processo_id,
            regra_original=padrao.regra_semantica,
            datas_sugeridas=datas_sugeridas,
            ai_interpretacao_texto=resposta,
        )
        db.add(arvore)
    db.flush()

    resultado = {"arvore_decisao_id": arvore.id, "datas_sugeridas": datas_sugeridas}
    if job:
        job.status = "concluido"
        job.resultado = resultado
    db.commit()

    return resultado
