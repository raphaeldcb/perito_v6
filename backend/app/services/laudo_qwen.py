"""Análise automática de vistorias via Qwen (Ollama local).

Processa dados da vistoria + modelo + fotos e gera parecer técnico automático.
"""
import json
import logging
import requests
from typing import Optional

from app.config.settings import settings
from app.utils import retry, get_circuit_breaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)
from app.models import Vistoria, ModeloVistoria


def _chamar_qwen(prompt: str) -> str:
    """Chama Qwen via Ollama local."""
    try:
        url = f"{settings.ollama_url}/api/generate"
        payload = {
            "model": settings.ollama_model or "perito-qwen",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3,
        }
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"Erro ao chamar Qwen: {e}")
        return ""


def formatar_dados_vistoria(vistoria: Vistoria) -> str:
    """Formata dados da vistoria em texto legível para análise."""
    texto = f"""
## VISTORIA #{vistoria.id}
**Modelo:** {vistoria.modelo.nome if vistoria.modelo else 'N/A'}
**Local:** {vistoria.local or 'N/A'}
**Data:** {vistoria.created_at.strftime('%d/%m/%Y') if vistoria.created_at else 'N/A'}
**GPS:** {vistoria.gps or 'N/A'}

### DADOS COLETADOS:
"""
    dados = vistoria.dados or {}

    # Tentar extrair labels do schema
    label_map = {}
    for secao in (vistoria.modelo.schema.get("secoes") or []):
        for campo in secao.get("campos", []):
            label_map[campo.get("key")] = campo.get("label", campo.get("key"))

    for chave, valor in dados.items():
        if chave.startswith("_") or not valor:
            continue
        label = label_map.get(chave, chave.replace("_", " ").title())

        if isinstance(valor, list):
            valor_str = ", ".join(str(v) for v in valor)
        elif isinstance(valor, dict):
            valor_str = json.dumps(valor, ensure_ascii=False, indent=1)[:200]
        else:
            valor_str = str(valor)

        texto += f"\n- **{label}:** {valor_str}"

    # Adicionar info de fotos
    if vistoria.fotos:
        texto += f"\n\n### FOTOS:\nTotal de {len(vistoria.fotos)} foto(s) anexada(s)."

    # Adicionar info de assinaturas
    if vistoria.assinaturas:
        texto += f"\n\n### ASSINANTES:\n"
        for a in vistoria.assinaturas:
            texto += f"- {a.nome} ({a.papel})"

    return texto


def gerar_laudo_vistoria(vistoria: Vistoria) -> str:
    """
    Gera parecer técnico em 5 blocos (Introdução, Achados, Análise, Conclusão, Recomendações).
    Usa Qwen via Ollama.
    """
    dados_formatados = formatar_dados_vistoria(vistoria)

    # PROMPT sistema
    sistema = f"""Você é um engenheiro experiente analisando relatórios de vistoria.
Seu objetivo é gerar um PARECER TÉCNICO estruturado e claro.
Responda APENAS em JSON válido, sem markdown ou formatação extra.
Use exatamente este formato:
{{
  "introducao": "Parágrafo introdutório com contexto da vistoria (2-3 linhas)",
  "achados": "Listagem dos principais achados da vistoria (5-8 linhas)",
  "analise": "Análise técnica fundamentada nos dados coletados (8-10 linhas)",
  "conclusao": "Conclusão e síntese do parecer (3-4 linhas)",
  "recomendacoes": "Recomendações e próximos passos (4-6 linhas)"
}}

IMPORTANTE: Responda APENAS com JSON válido, sem comentários ou texto adicional.
Se houver dúvida sobre qualidade dos dados, mencione na conclusão.
"""

    prompt = f"""{sistema}

## DADOS DA VISTORIA PARA ANÁLISE:
{dados_formatados}

Gere o parecer técnico:"""

    resposta = _chamar_qwen(prompt)

    # Tentar parsear JSON
    try:
        laudo_dict = json.loads(resposta)
        laudo_texto = f"""PARECER TÉCNICO DE VISTORIA #{vistoria.id}

INTRODUÇÃO
{laudo_dict.get('introducao', 'N/A')}

ACHADOS
{laudo_dict.get('achados', 'N/A')}

ANÁLISE
{laudo_dict.get('analise', 'N/A')}

CONCLUSÃO
{laudo_dict.get('conclusao', 'N/A')}

RECOMENDAÇÕES
{laudo_dict.get('recomendacoes', 'N/A')}
"""
    except json.JSONDecodeError:
        # Se falhar, usar resposta bruta
        laudo_texto = f"""PARECER TÉCNICO DE VISTORIA #{vistoria.id}

[RESPOSTA BRUTA DO QWEN]
{resposta}

NOTA: A resposta do modelo não foi estruturada em JSON conforme esperado.
Verifique manualmente o parecer acima.
"""

    return laudo_texto


def resumo_rpido_vistoria(vistoria: Vistoria, maxlen: int = 200) -> str:
    """Gera um resumo muito breve (para card/preview)."""
    dados = vistoria.dados or {}
    resumo_items = []

    for chave in ["situacao", "condicoes_ocupacao", "descricao_atividades", "objeto"]:
        if chave in dados and dados[chave]:
            val = dados[chave]
            if isinstance(val, list):
                resumo_items.append(", ".join(val)[:100])
            else:
                resumo_items.append(str(val)[:100])

    resumo = " | ".join(resumo_items)[:maxlen] + "..."
    return resumo or "Vistoria sem dados resumidos"
