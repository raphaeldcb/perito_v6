"""
Google OAuth 2.0 + Maps API Authentication
Usa credenciais do client_secret.json
"""
import os
import json
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import logging

logger = logging.getLogger(__name__)

CLIENT_SECRET_PATH = os.environ.get("GOOGLE_CLIENT_SECRET_PATH", 
    "/Users/ipc_server/Downloads/client_secret_338909438706-3qc698ql620lcm2d2jsmfabukncjqf10.apps.googleusercontent.com.json")

SCOPES = [
    'https://www.googleapis.com/auth/maps-platform.routesapi',
    'https://www.googleapis.com/auth/maps-platform.mapsplatform'
]

def obter_token_google() -> str:
    """Obtém token OAuth 2.0 válido do client_secret"""
    try:
        if not os.path.exists(CLIENT_SECRET_PATH):
            logger.error(f"client_secret não encontrado: {CLIENT_SECRET_PATH}")
            return None
        
        # Para aplicações desktop/server, usar API key diretamente
        # OAuth é para user-facing apps. Para backend, usar API Key.
        with open(CLIENT_SECRET_PATH, 'r') as f:
            config = json.load(f)
        
        # Extrair dados de autenticação
        return config.get("installed", {}).get("client_id")
    except Exception as e:
        logger.error(f"Erro autenticação Google: {e}")
        return None

def obter_api_key_google() -> str:
    """Retorna API key (extraída de config ou env)"""
    # Se tiver em .env, usar
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if api_key:
        return api_key
    
    # Fallback: ler do client_secret (se houver field de API key)
    try:
        with open(CLIENT_SECRET_PATH, 'r') as f:
            config = json.load(f)
        return config.get("api_key")  # Se existir
    except:
        return None

def autenticar_maps_api() -> dict:
    """Prepara headers de autenticação para Google Maps API"""
    api_key = obter_api_key_google()
    
    return {
        "Authorization": f"Bearer {obter_token_google()}" if obter_token_google() else None,
        "X-Goog-Api-Key": api_key if api_key else None
    }
