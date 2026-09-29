"""
Service layer for deslocamento (travel distance/displacement) tools.

Combines functionality from:
- deslocamento_v2.py (Google Maps + flight estimation)
- deslocamento_pedagio.py (RotasBrasil real-time toll calculation)

Includes pedagio calculation logic (both automatic estimates and RotasBrasil API calls).
"""

import httpx
import logging
from typing import Dict, Any, Optional
from app.services.google_maps_service import calcular_rota
from app.services.google_flights_scraper import estimar_preco_aviao

logger = logging.getLogger(__name__)

# RotasBrasil API configuration
ROTAS_BRASIL_TOKEN = "fd4f1ea0ca561332ff6147710da65201"
ROTAS_BRASIL_API = "https://rotasbrasil.com.br/api/v3"


def calcular_pedagio_automatico(distancia_km: float) -> float:
    """
    Estima pedágio baseado em distância (simplificado).

    Used as fallback when RotasBrasil API is unavailable.
    TODO: integrar com API real de pedágio (ABCR, ETC)

    Args:
        distancia_km: Total distance in kilometers (round trip)

    Returns:
        Estimated toll amount in BRL
    """
    if distancia_km < 50:
        return 0.0
    elif distancia_km < 100:
        return 15.0
    elif distancia_km < 200:
        return 35.0
    elif distancia_km < 500:
        return 80.0
    else:
        return 150.0


async def calcular_pedagio_rotasbrasil(
    origem: str,
    destino: str,
    veiculo: str = "caminhao",
    eixos: int = 6
) -> Dict[str, Any]:
    """
    Calcula pedágio em tempo real via API RotasBrasil.

    Args:
        origem: Origin (city or postal code, e.g., "Curitiba,PR" or "88525-600")
        destino: Destination (e.g., "Florianópolis,SC")
        veiculo: Vehicle type (caminhao, onibus, carro, moto)
        eixos: Number of axles (2-6)

    Returns:
        Dictionary with pedagio_total, ida, volta, distancia_km, tempo_viagem, pontos

    Raises:
        Exception: If RotasBrasil API fails or returns invalid data
    """
    try:
        # Format route points as expected by RotasBrasil API
        pontos = f"{origem};{destino}"

        # Build RotasBrasil API URL
        url = f"{ROTAS_BRASIL_API}?pontos={pontos}&veiculo={veiculo}&eixos={eixos}&token={ROTAS_BRASIL_TOKEN}"

        logger.info(f"Calling RotasBrasil API: {url}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # Extract data from response
        pedagio_ida = float(data.get("pedagio", 0))
        distancia = int(data.get("distancia", 0))
        tempo = data.get("tempo", "0h")

        return {
            "pedagio_total": pedagio_ida * 2,  # Round trip
            "ida": pedagio_ida,
            "volta": pedagio_ida,
            "distancia_km": distancia,
            "tempo_viagem": tempo,
            "pontos": pontos
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling RotasBrasil API: {e}")
        raise Exception("Serviço de pedágio indisponível")
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing RotasBrasil response: {e}")
        raise Exception("Erro ao processar dados de pedágio")
    except Exception as e:
        logger.error(f"Unexpected error in RotasBrasil call: {e}")
        raise Exception("Erro ao calcular pedágio")


async def calcular_deslocamento_completo(
    origem: str,
    destino: str,
    ida_volta: bool = True,
    pedagio_manual: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calcula deslocamento completo: rota Google Maps + pedágio automático + comparativo avião.

    This is the main orchestration function combining:
    1. Route calculation (Google Maps)
    2. Toll calculation (manual input or automatic)
    3. Flight comparison (if distance > 600km)

    Args:
        origem: Origin city/address
        destino: Destination city/address
        ida_volta: Round trip flag
        pedagio_manual: Manual toll value (if None, calculates automatically)

    Returns:
        Complete displacement calculation with comparisons
    """
    # Get route from Google Maps
    rota = calcular_rota(origem, destino)
    if rota["erro"]:
        raise Exception(f"Erro na rota: {rota['erro']}")

    distancia_ida = rota["distancia_km"]
    distancia_total = distancia_ida * 2 if ida_volta else distancia_ida

    # Calculate toll: use manual input or automatic estimate
    if pedagio_manual is not None:
        pedagio = pedagio_manual * (2 if ida_volta else 1)
    else:
        pedagio = calcular_pedagio_automatico(distancia_total)

    # Car cost: R$ 1.20/km + toll
    custo_km_carro = distancia_total * 1.20
    custo_total_carro = custo_km_carro + pedagio

    # Comparison: if > 600km, show flight option with real price
    comparativo = None
    if distancia_ida > 600:
        # Flight: get real price from Google Flights
        voo_info = estimar_preco_aviao(distancia_ida)
        preco_aviao_passageiro = voo_info["preco_por_passageiro"]

        # Flight time: 1/3 of car time
        tempo_aviao = max(2, rota["tempo_horas"] / 3)
        tempo_aviao_total = tempo_aviao if not ida_volta else tempo_aviao * 2

        # Car total time
        tempo_carro_total = rota["tempo_horas"] * (2 if ida_volta else 1)

        comparativo = {
            "carro": {
                "distancia_km": round(distancia_total, 2),
                "tempo_horas": round(tempo_carro_total, 2),
                "pedagio": round(pedagio, 2),
                "custo_km": round(custo_km_carro, 2),
                "custo_total": round(custo_total_carro, 2),
                "moeda": "BRL",
                "tipo": "ida e volta"
            },
            "aviao": {
                "distancia_km": round(distancia_ida, 2),
                "tempo_horas": round(tempo_aviao_total, 2),
                "preco_por_passageiro": preco_aviao_passageiro,
                "pedagio": 0.0,
                "moeda": "BRL",
                "tipo": "ida e volta",
                "nota": voo_info.get("nota", "Preço estimado - consultar Google Flights para preço atualizado"),
                "economia_tempo": f"{round(tempo_carro_total - tempo_aviao_total, 1)}h menos"
            },
            "recomendacao": "carro" if round(custo_total_carro, 2) < preco_aviao_passageiro else "aviao",
            "economia": {
                "se_carro": f"Economiza R$ {round(max(0, preco_aviao_passageiro - custo_total_carro), 2)} vs avião",
                "se_aviao": f"Economiza {round(tempo_carro_total - tempo_aviao_total, 1)}h vs carro"
            }
        }

    return {
        "distancia_km": round(distancia_total, 2),
        "tempo_horas": round(rota["tempo_horas"] * (2 if ida_volta else 1), 2),
        "pedagio": round(pedagio, 2),
        "custo_total": round(custo_total_carro, 2),
        "detalhes": {
            "origem": origem,
            "destino": destino,
            "ida_volta": ida_volta,
            "custo_km": round(custo_km_carro, 2),
            "polyline": rota["polyline"],
            "modo": "carro" if distancia_ida <= 600 else "comparativo"
        },
        "comparativo": comparativo
    }
