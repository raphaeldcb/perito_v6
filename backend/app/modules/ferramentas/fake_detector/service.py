"""Service — Geração de laudo forense para fake detector."""
from typing import Dict


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
