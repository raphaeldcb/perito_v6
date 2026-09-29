"""
Google Maps Distance Matrix API helper
"""
import logging
import googlemaps
from app.config import settings

logger = logging.getLogger(__name__)


async def calcular_distancia_google_maps(origem_cep: str, destino_cep: str) -> float:
    """
    Calcula distância real entre dois CEPs usando Google Maps Distance Matrix API.

    Args:
        origem_cep: CEP de origem (ex: "01310100")
        destino_cep: CEP de destino (ex: "20040020")

    Returns:
        Distância em km, ou None se erro/chave não configurada
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY não configurada, usando cálculo local")
        return None

    try:
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY, timeout=10)
        result = gmaps.distance_matrix(
            origins=origem_cep,
            destinations=destino_cep,
            mode="driving",
            language="pt-BR"
        )

        if result["rows"][0]["elements"][0]["status"] == "OK":
            distance_meters = result["rows"][0]["elements"][0]["distance"]["value"]
            distance_km = distance_meters / 1000
            logger.info(f"Google Maps: {origem_cep} → {destino_cep} = {distance_km:.2f}km")
            return distance_km
        else:
            logger.warning(f"Google Maps: origem ou destino inválido")
            return None

    except Exception as e:
        logger.error(f"Google Maps API error: {e}")
        return None
