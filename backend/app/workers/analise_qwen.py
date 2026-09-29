"""Análise de intimações pendentes com Qwen (DashScope) ou Ollama.

Sem chave hardcoded: usa settings.qwen_api_key e settings.ollama_url do
ambiente. Falha de análise marca a intimação com status 'erro' e a mensagem
real — nunca finge sucesso.

Fluxo com arquivos: PDF → OCR/pypdf → TXT → Qwen → JSON/MD arquivo → BD
"""
import json
import logging
import os

import requests

from app.config import settings
from app.models import Intimacao
from app.services.database import SessionLocal
from app.services.ocr_processor import extrair_texto_com_ocr
from app.services.intimacao_formatter import formatar_resultado, salvar_markdown, salvar_json

logger = logging.getLogger(__name__)

PROMPT = """Você é um perito jurídico. Analise esta intimação e retorne APENAS JSON válido com:
{{"numero_processo": "...", "tipo": "...", "prazo_dias": 0, "juiz": "...", "vara": "...",
"partes": [], "quesitos": [], "urgencia": "baixa|media|alta", "resumo": "..."}}

Texto da intimação:
{texto}
"""


def _texto_da_intimacao(intimacao: Intimacao) -> tuple[str, str]:
    """Retorna (texto, txt_path) — salva TXT em arquivo se PDF."""
    if intimacao.conteudo:
        return intimacao.conteudo[:15000], None

    if intimacao.pdf_path:
        try:
            # OCR com fallback pypdf + salva em arquivo
            texto = extrair_texto_com_ocr(intimacao.pdf_path)
            pdf_dir = os.path.dirname(intimacao.pdf_path)
            txt_path = os.path.join(pdf_dir, "texto.txt")
            return texto[:15000], txt_path
        except Exception as e:
            raise RuntimeError(f"Falha ao extrair texto do PDF {intimacao.pdf_path}: {e}")

    raise RuntimeError("Intimação sem conteúdo e sem PDF")


def _extrair_json(texto: str) -> dict:
    inicio = texto.find("{")
    fim = texto.rfind("}") + 1
    if inicio < 0 or fim <= inicio:
        raise ValueError(f"Resposta do modelo sem JSON: {texto[:200]!r}")
    return json.loads(texto[inicio:fim])


def _analisar_ollama(texto: str) -> dict:
    resp = requests.post(
        f"{settings.ollama_url}/api/generate",
        json={
            "model": os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:32b"),
            "prompt": PROMPT.format(texto=texto),
            "stream": False,
            "format": "json",
        },
        timeout=180,
    )
    resp.raise_for_status()
    return _extrair_json(resp.json().get("response", ""))


def _analisar_dashscope(texto: str) -> dict:
    # Formato correto da API generation do DashScope: envelope input/parameters
    resp = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        headers={
            "Authorization": f"Bearer {settings.qwen_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.qwen_model,
            "input": {"messages": [{"role": "user", "content": PROMPT.format(texto=texto)}]},
            "parameters": {"result_format": "message", "temperature": 0.3},
        },
        timeout=60,
    )
    resp.raise_for_status()
    corpo = resp.json()
    conteudo = corpo["output"]["choices"][0]["message"]["content"]
    return _extrair_json(conteudo)


def analisar_texto(texto: str) -> dict:
    """Tenta Ollama primeiro (local, sem custo); DashScope como fallback."""
    erros = []
    try:
        return _analisar_ollama(texto)
    except Exception as e:
        erros.append(f"ollama: {e}")

    if settings.qwen_api_key:
        try:
            return _analisar_dashscope(texto)
        except Exception as e:
            erros.append(f"dashscope: {e}")
    else:
        erros.append("dashscope: QWEN_API_KEY não configurada")

    raise RuntimeError(" | ".join(erros))


def _enfileirar_para_agente(db, intimacao: Intimacao) -> None:
    """Modo 'agente': a análise roda no Ollama LOCAL do Mac via mac_agent.

    A VPS não tem GPU nem Ollama — o Mac tem (Qwen local instalado, sem API
    key). O job leva o texto quando existe; senão o agente baixa o PDF via
    GET /api/v1/jobs/{id}/arquivo.
    """
    from app.models import Job

    job_aberto = (
        db.query(Job)
        .filter(
            Job.tipo == "analise_ia",
            Job.status.in_(["na_fila", "processando"]),
            Job.payload["intimacao_id"].astext == str(intimacao.id),
        )
        .first()
    )
    if job_aberto:
        return

    payload = {"intimacao_id": intimacao.id}
    if intimacao.conteudo:
        payload["conteudo"] = intimacao.conteudo[:15000]
    elif intimacao.pdf_path:
        payload["pdf_path"] = intimacao.pdf_path
    db.add(Job(tipo="analise_ia", payload=payload, status="na_fila"))
    intimacao.status = "processando"
    logger.info(f"📨 Intimação {intimacao.id} enfileirada para análise no Mac")


def processar_intimacoes_pendentes() -> int:
    """Analisa intimações pendentes. Sessão nova por chamada; commit por item.

    ANALISE_MODO=agente (padrão): enfileira para o Ollama local do Mac.
    ANALISE_MODO=local: analisa aqui mesmo (exige OLLAMA_URL acessível da VPS).

    Fluxo com arquivos: texto → Qwen → JSON/MD arquivo → BD
    """
    modo = os.environ.get("ANALISE_MODO", "agente")
    db = SessionLocal()
    processadas = 0
    try:
        pendentes = db.query(Intimacao).filter(Intimacao.status == "pendente").limit(20).all()
        for intimacao in pendentes:
            if modo == "agente":
                _enfileirar_para_agente(db, intimacao)
            else:
                try:
                    texto, txt_path = _texto_da_intimacao(intimacao)
                    intimacao.txt_path = txt_path  # Salvo automaticamente por OCR

                    # Análise Qwen
                    dados = analisar_texto(texto)

                    # Salvar JSON arquivo
                    if intimacao.pdf_path:
                        pdf_dir = os.path.dirname(intimacao.pdf_path)
                        json_path = os.path.join(pdf_dir, "analise.json")
                        salvar_json(dados, json_path)
                        intimacao.json_path = json_path

                        # Salvar MD formatado
                        md_content = formatar_resultado(dados, texto, intimacao.processo.numero_cnj if intimacao.processo else "")
                        md_path = os.path.join(pdf_dir, "analise.md")
                        salvar_markdown(md_content, md_path)
                        intimacao.md_path = md_path

                    intimacao.dados_estruturados = dados
                    intimacao.status = "analisada"
                    intimacao.erros = None
                    logger.info(f"🤖 Intimação {intimacao.id} analisada → JSON + MD salvos")
                except Exception as e:
                    intimacao.status = "erro"
                    intimacao.erros = str(e)[:2000]
                    logger.error(f"❌ Intimação {intimacao.id}: {e}")
            db.commit()
            processadas += 1
    finally:
        db.close()
    return processadas
