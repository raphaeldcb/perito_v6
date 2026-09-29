import logging
import os
import json
import requests
from sqlalchemy.orm import Session
from app.models import Laudo, LaudoVersao, Processo

logger = logging.getLogger(__name__)

QWEN_URL = os.getenv("QWEN_URL", "http://localhost:11434")
QWEN_MODEL = os.getenv("QWEN_MODEL", "batiai/qwen3.6-35b:iq4")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

PROMPT_TEMPLATE = """ROLE: Você é perito judicial especializado em {tipo_laudo}.

CONTEXTO:
- Tipo de Laudo: {tipo_laudo}
- Número do Processo: {numero_processo}
- Vara/Tribunal: {tribunal}
- Partes: {autor} vs {reu}
- Quesitos: {quesitos_json}

DOCUMENTOS ANEXOS:
{pdf_texto}

TAREFA:
Elabore RASCUNHO de Laudo Pericial seguindo a estrutura da norma técnica.

ESTRUTURA OBRIGATÓRIA:

## 1. IDENTIFICAÇÃO
- Número do processo
- Vara/Juiz
- Partes e qualificação
- Perito e qualificação (CRC/CREA)

## 2. SÍNTESE DO OBJETO
- Resumo da lide
- Objetivo específico da perícia

## 3. METODOLOGIA
- Procedimentos utilizados
- Normas aplicadas

## 4. RELATO DAS DILIGÊNCIAS
- Datas, locais, documentos
- Limitações encontradas

## 5. ANÁLISE TÉCNICA
- Discussão detalhada
- Memória de cálculo (se aplicável)
- Fundamentação legal/técnica

## 6. RESPOSTAS AOS QUESITOS
- Resposta numerada para CADA quesito
- Fundamentação objetiva

## 7. CONCLUSÃO
- Parecer técnico final
- Síntese dos resultados

## 8. ENCERRAMENTO
- Local, data
- Assinatura com CRC/CREA

REQUISITOS:
1. Linguagem técnica clara (sem subjetividades)
2. CADA conclusão com EVIDÊNCIA (cite fls. XXX)
3. Neutralidade absoluta
4. Se dados insuficientes, aponte limitação
5. Nenhum artigo/lei/norma pode ser "alucinação"
6. Valores em conclusão = valores em análise (consistência)

FORMATO: Markdown estruturado com títulos ##, listas e tabelas.
OUTPUT: Rascunho em Markdown pronto para auditoria."""


def _call_ollama(prompt: str) -> str:
    """Chama Ollama localmente."""
    try:
        response = requests.post(
            f"{QWEN_URL}/api/generate",
            json={
                "model": QWEN_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 40
            },
            timeout=300
        )
        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.text}")
        return response.json()["response"]
    except Exception as e:
        logger.warning(f"Ollama falhou: {e}")
        raise


def _call_dashscope(prompt: str) -> str:
    """Fallback: DashScope (Qwen cloud)."""
    try:
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            headers={
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen-turbo",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=300
        )
        if response.status_code != 200:
            raise Exception(f"DashScope error: {response.text}")
        return response.json()["output"]["text"]
    except Exception as e:
        logger.error(f"DashScope também falhou: {e}")
        raise


def gerar_rascunho(laudo_id: int, db: Session) -> LaudoVersao:
    """Gera rascunho com Qwen, com fallback para DashScope."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise ValueError(f"Laudo {laudo_id} não encontrado")

    processo = db.query(Processo).filter(Processo.id == laudo.processo_id).first()
    quesitos = json.loads(laudo.quesitos) if laudo.quesitos else []

    pdf_texto = ""
    if hasattr(processo, "arquivos") and processo.arquivos:
        try:
            for arquivo in processo.arquivos:
                if hasattr(arquivo, "conteudo"):
                    pdf_texto += f"\n{arquivo.conteudo[:2000]}"
        except Exception as e:
            logger.warning(f"Não conseguiu extrair PDFs: {e}")

    prompt = PROMPT_TEMPLATE.format(
        tipo_laudo=laudo.tipo_laudo or "Contábil",
        numero_processo=getattr(processo, "numero_cnj", None) or "N/A",
        tribunal=processo.tribunal if hasattr(processo, "tribunal") else "N/A",
        autor=processo.autor if hasattr(processo, "autor") else "Não informado",
        reu=processo.reu if hasattr(processo, "reu") else "Não informado",
        quesitos_json=json.dumps(quesitos, ensure_ascii=False),
        pdf_texto=pdf_texto[:8000] if pdf_texto else "[Documentos não fornecidos]"
    )

    rascunho_md = None
    try:
        logger.info(f"Tentando Ollama para laudo {laudo_id}...")
        rascunho_md = _call_ollama(prompt)
    except Exception as e:
        logger.warning(f"Ollama falhou, tentando DashScope: {e}")
        try:
            if QWEN_API_KEY:
                rascunho_md = _call_dashscope(prompt)
            else:
                raise ValueError("DashScope não configurado (QWEN_API_KEY ausente)")
        except Exception as e2:
            logger.error(f"Ambos os serviços falharam: {e2}")
            rascunho_md = f"[ERRO ao gerar rascunho]\n\nTentativa Ollama: {e}\nTentativa DashScope: {e2}\n\nPor favor, verifique a configuração do Qwen."

    numero_versao = db.query(LaudoVersao).filter(
        LaudoVersao.laudo_id == laudo_id
    ).count() + 1

    versao = LaudoVersao(
        laudo_id=laudo_id,
        numero_versao=numero_versao,
        conteudo_markdown=rascunho_md,
        gerado_por="qwen"
    )
    db.add(versao)
    db.commit()
    db.refresh(versao)

    logger.info(f"Rascunho v{numero_versao} gerado para laudo {laudo_id}")
    return versao
