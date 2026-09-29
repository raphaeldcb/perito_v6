"""
Google Maps Distance Matrix API + Routes API
Autenticação via OAuth client_secret.json
"""
import os
import requests
from typing import Dict, Optional
import logging
from .google_auth_service import obter_api_key_google

logger = logging.getLogger(__name__)

# Usar API Key (obtida do client_secret ou .env)
GOOGLE_MAPS_API_KEY = obter_api_key_google()
BASE_URL = "https://maps.googleapis.com/maps/api"

def calcular_rota(origem: str, destino: str) -> Dict:
    """
    Calcula rota entre 2 endereços via Google Maps Directions API
    
    Args:
        origem: "Rua X, São Paulo, SP" ou coordenadas "lat,lng"
        destino: idem
    
    Returns:
        {
            "distancia_km": 150.5,
            "tempo_horas": 2.5,
            "tempo_minutos": 150,
            "polyline": "...",
            "status": "OK",
            "erro": None
        }
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY não configurada. Usando valores dummy.")
        return {
            "distancia_km": 100.0,
            "tempo_horas": 1.5,
            "tempo_minutos": 90,
            "polyline": None,
            "status": "NO_KEY",
            "erro": "API key não configurada"
        }
    
    try:
        response = requests.get(f"{BASE_URL}/directions/json", params={
            "origin": origem,
            "destination": destino,
            "key": GOOGLE_MAPS_API_KEY,
            "language": "pt-BR",
            "region": "BR"
        }, timeout=10)
        
        if response.status_code != 200:
            return {
                "distancia_km": 0, 
                "tempo_horas": 0, 
                "tempo_minutos": 0,
                "polyline": None,
                "status": "ERROR",
                "erro": f"HTTP {response.status_code}"
            }
        
        data = response.json()
        if data.get("status") != "OK":
            logger.warning(f"Google Maps status: {data.get('status')}")
            return {
                "distancia_km": 0, 
                "tempo_horas": 0,
                "tempo_minutos": 0,
                "polyline": None,
                "status": data.get("status"),
                "erro": f"Status: {data.get('status')}"
            }
        
        if not data.get("routes"):
            return {
                "distancia_km": 0,
                "tempo_horas": 0,
                "tempo_minutos": 0,
                "polyline": None,
                "status": "NO_ROUTE",
                "erro": "Nenhuma rota encontrada"
            }
        
        rota = data["routes"][0]["legs"][0]
        distancia_m = rota["distance"]["value"]
        tempo_s = rota["duration"]["value"]
        
        return {
            "distancia_km": round(distancia_m / 1000, 2),
            "tempo_horas": round(tempo_s / 3600, 2),
            "tempo_minutos": round(tempo_s / 60, 0),
            "polyline": data["routes"][0].get("overview_polyline", {}).get("points"),
            "status": "OK",
            "erro": None
        }
    except Exception as e:
        logger.error(f"Erro Google Maps: {e}")
        return {
            "distancia_km": 0,
            "tempo_horas": 0,
            "tempo_minutos": 0,
            "polyline": None,
            "status": "EXCEPTION",
            "erro": str(e)
        }

def calcular_tempo_viagem(distancia_km: float) -> float:
    """Estima tempo de viagem em horas (velocidade média 80 km/h)"""
    velocidade_media = 80  # km/h (considerando rodovia)
    return round(distancia_km / velocidade_media, 2)
