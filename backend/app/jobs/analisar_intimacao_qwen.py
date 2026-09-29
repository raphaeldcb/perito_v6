"""Job: Analisa intimação com Qwen 3.6 local"""
import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://172.18.0.1:11434"
MODEL = "perito-qwen"

def analisar_intimacao(texto: str, laudo_id: int) -> Dict:
    """
    Analisa texto de intimação via Qwen local
    
    Returns:
        {
            "tipo": "citacao|intimacao|oficio",
            "urgencia": "alta|media|baixa",
            "prazo_dias": 30,
            "partes": ["autor", "reu"],
            "ai_interpretacao": "...",
            "confianca": 0.85,
            "erro": None
        }
    """
    try:
        prompt = f"""Analise este texto de intimação judicial:

{texto[:2000]}

Responda em JSON:
{{
    "tipo": "tipo de ato (citacao/intimacao/oficio)",
    "urgencia": "urgencia (alta/media/baixa)",
    "prazo_dias": numero de dias para atender,
    "partes": ["lista", "de", "partes"],
    "resumo": "resumo executivo"
}}"""
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama erro: {response.status_code}")
        
        resultado = response.json()
        texto_resposta = resultado.get("response", "{}")
        
        import json
        try:
            analise = json.loads(texto_resposta)
        except:
            analise = {
                "tipo": "intimacao",
                "urgencia": "media",
                "prazo_dias": 30,
                "partes": [],
                "resumo": texto_resposta[:200]
            }
        
        return {
            "tipo": analise.get("tipo", "intimacao"),
            "urgencia": analise.get("urgencia", "media"),
            "prazo_dias": analise.get("prazo_dias", 30),
            "partes": analise.get("partes", []),
            "ai_interpretacao": analise.get("resumo", ""),
            "confianca": 0.8,
            "erro": None
        }
    except Exception as e:
        logger.error(f"Erro Qwen análise: {e}")
        return {
            "tipo": "intimacao",
            "urgencia": "media",
            "prazo_dias": 30,
            "partes": [],
            "ai_interpretacao": "",
            "confianca": 0.0,
            "erro": str(e)
        }
