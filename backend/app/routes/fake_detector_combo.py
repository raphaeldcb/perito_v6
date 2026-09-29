"""
🎭 ROTA: Fake Detector Combo — 100% Confiança + Laudo Automático
POST /api/v1/media/fake-detector-combo
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime

# Adicionar scripts ao path
scripts_path = str(Path(__file__).parent.parent.parent / "scripts")
sys.path.insert(0, scripts_path)

try:
    from fake_detector_combo import FakeDetectorCombo
except ImportError as e:
    raise RuntimeError(f"Failed to import FakeDetectorCombo from {scripts_path}: {e}")
import asyncio

router = APIRouter(prefix="/api/v1/media", tags=["fake-detector"])


@router.get("/fake-detector-combo/status")
async def status_fake_detector():
    """Status do detector combo — 7 APIs disponíveis"""
    apis_status = {
        'deepware': {
            'configurada': bool(os.getenv('DEEPWARE_API_KEY')),
            'descricao': 'Deepware Scanner (melhor para vídeos)'
        },
        'reality_defender': {
            'configurada': bool(os.getenv('REALITY_DEFENDER_KEY')),
            'descricao': 'Reality Defender (imagens + vídeos)'
        },
        'sensity': {
            'configurada': bool(os.getenv('SENSITY_API_KEY')),
            'descricao': 'Sensity (áudio + vídeo, enterprise)'
        },
        'azure': {
            'configurada': bool(os.getenv('AZURE_API_KEY')),
            'descricao': 'Azure Video Indexer'
        },
        'google': {
            'configurada': bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
            'descricao': 'Google Cloud Video Intelligence'
        },
        'ibm': {
            'configurada': bool(os.getenv('IBM_API_KEY')),
            'descricao': 'IBM Watson Visual Recognition'
        },
        'local': {
            'configurada': True,
            'descricao': 'Análise Local (sempre disponível, grátis)'
        }
    }

    configuradas = sum(1 for v in apis_status.values() if v['configurada'])

    return {
        "status": "operacional",
        "apis_total": len(apis_status),
        "apis_configuradas": configuradas,
        "apis": apis_status,
        "recomendacao": {
            "quick": "local (rápido, grátis)",
            "balanced": "deepware + local (bom custo/benefício)",
            "full": "all (máxima confiança, mais lento/caro)",
            "100_confidence": "Exige todas as APIs concordarem"
        }
    }


@router.post("/fake-detector-combo")
async def analisar_fake_combo(
    file: UploadFile = File(...),
    usar_apis: str = Query("all", description="all, local, ou deepware,reality_defender,..."),
    tipo_laudo: str = Query("simples", description="simples ou completo"),
    background_tasks: BackgroundTasks = None
):
    """
    Análise Fake Detector + Geração de Laudo (Simples ou Completo)

    ### Parâmetros:
    - **file**: Arquivo (JPG, PNG, MP4, MP3, etc)
    - **usar_apis**: Quais APIs usar
      - `all` = Todas as 7 (melhor, mais lento/caro)
      - `local` = Só análise local (rápido, grátis, menos preciso)
      - `deepware,google,azure` = Selecionadas
    - **tipo_laudo**: Tipo de relatório
      - `simples` = Relatório técnico básico (veredicto + confiança)
      - `completo` = Laudo pericial completo (detalhado, análise estatística)

    ### Response:
    Retorna análise de consenso + laudo (simples ou completo)
    """

    temp_path = None

    try:
        # 1. Salvar arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            temp_path = tmp.name
            conteudo = await file.read()
            tmp.write(conteudo)

        # 2. Parse das APIs
        if usar_apis == "all":
            apis_lista = None
        elif usar_apis == "local":
            apis_lista = ["local"]
        else:
            apis_lista = [a.strip() for a in usar_apis.split(",")]

        # 3. Análise com timeout máximo 30 segundos
        detector = FakeDetectorCombo()
        try:
            resultado = await asyncio.wait_for(
                detector.analisar_combo(temp_path, usar_apis=apis_lista),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Análise excedeu timeout de 30 segundos — use 'local' para resultado rápido")

        # 4. Gerar laudo
        laudo = gerar_laudo_fake_detector(resultado, tipo_laudo)

        # 5. Response
        response_data = {
            "arquivo": resultado.arquivo,
            "tipo": resultado.tipo,
            "hash": resultado.hash,
            "tamanho_mb": resultado.tamanho_mb,
            "is_fake": resultado.is_fake,
            "confianca_minima": resultado.confianca_minima,
            "confianca_media": resultado.confianca_media,
            "todas_concordam": resultado.todas_concordam,
            "divergencias": resultado.divergencias,
            "status": resultado.status,
            "recomendacao": resultado.recomendacao,
            "resultados_apis": [
                {
                    "api": r.api,
                    "is_fake": r.is_fake,
                    "confidence": r.confidence,
                    "tempo_ms": r.tempo_ms,
                    "erro": r.erro
                }
                for r in resultado.resultados_apis
            ],
            "tempo_total_ms": resultado.tempo_total_ms,
            "timestamp": resultado.timestamp,
            "laudo": laudo
        }

        # 6. Limpeza
        if background_tasks:
            background_tasks.add_task(os.remove, temp_path)

        return JSONResponse(status_code=200, content=response_data)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Análise expirou (timeout) — tente novamente com usar_apis=local")
    except Exception as e:
        import traceback
        import logging
        logging.error(f"Fake Detector error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


def gerar_laudo_fake_detector(resultado, tipo_laudo: str) -> Dict:
    """Gera laudo forense (simples ou completo)"""

    titulo = "LAUDO TÉCNICO DE ANÁLISE FORENSE" if tipo_laudo == "completo" else "PARECER TÉCNICO - ANÁLISE RÁPIDA"

    laudo = {
        "titulo": titulo,
        "data_analise": resultado.timestamp,
        "arquivo": resultado.arquivo,
        "tipo_midia": resultado.tipo,
        "hash_md5": resultado.hash,
        "tamanho_bytes": resultado.tamanho_mb * 1024 * 1024,
    }

    if tipo_laudo == "simples":
        total_apis = len(resultado.resultados_apis) if resultado.resultados_apis else 1
        concordancia = "100%" if resultado.todas_concordam else f"{100 - (len(resultado.divergencias)*100/total_apis):.0f}%" if resultado.resultados_apis else "N/A"
        laudo.update({
            "conclusao": f"{'🚨 DETECTADO DEEPFAKE' if resultado.is_fake else '✅ MIDIA LEGÍTIMA'}",
            "confianca_media": f"{resultado.confianca_media:.1f}%",
            "apis_concordam": concordancia,
            "recomendacao": resultado.recomendacao,
            "apis_testadas": len(resultado.resultados_apis),
        })
    else:  # completo
        laudo.update({
            "resumo_executivo": {
                "veredicto": f"{'🚨 DEEPFAKE DETECTADO' if resultado.is_fake else '✅ MIDIA AUTÊNTICA'}",
                "nivel_confianca": f"{resultado.confianca_media:.1f}%",
                "consenso_apis": "100% concordância" if resultado.todas_concordam else f"Divergências: {resultado.divergencias}",
            },
            "metodologia": "Análise de consenso com 7 APIs especializadas em detecção de deepfake (Deepware, Reality Defender, Sensity, Azure, Google, IBM, Local)",
            "resultados_detalhados": [
                {
                    "api": r.api,
                    "veredicto": "🚨 Fake" if r.is_fake else "✅ Legítimo",
                    "confianca": f"{r.confidence:.1f}%",
                    "tempo_analise_ms": r.tempo_ms,
                }
                for r in resultado.resultados_apis
            ],
            "analise_estatistica": {
                "confianca_minima": f"{resultado.confianca_minima:.1f}%",
                "confianca_maxima": f"{resultado.confianca_media:.1f}%",
                "desvio": f"{(resultado.confianca_media - resultado.confianca_minima) / 2:.1f}%",
                "apis_concordam": len([r for r in resultado.resultados_apis if r.is_fake == resultado.is_fake]),
                "total_apis": len(resultado.resultados_apis),
            },
            "conclusao_tecnica": resultado.recomendacao,
            "proximos_passos": [
                "✅ Análise conclusiva — nenhuma verificação adicional necessária" if resultado.todas_concordam
                else "⚠️ Divergências entre APIs — recomenda-se análise manual complementar"
            ],
        })

    return laudo


@router.post("/fake-detector-combo/configurar")
async def configurar_apis(config: Dict[str, str]):
    """
    Configurar API keys (use em produção com segurança — prefira .env ou Vault)

    Exemplo:
    ```bash
    curl -X POST http://localhost:8000/api/v1/media/fake-detector-combo/configurar \
      -H "Content-Type: application/json" \
      -d '{
        "DEEPWARE_API_KEY": "sk_live_xxx",
        "REALITY_DEFENDER_KEY": "rd_key_xxx"
      }'
    ```
    """
    try:
        for chave, valor in config.items():
            os.environ[chave] = valor
        return {"status": "configurado", "variaveis": list(config.keys())}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
