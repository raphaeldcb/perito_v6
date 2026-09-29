"""
Google Flights Web Scraper — Busca preços reais de passagens aéreas
Integração com Selenium/Browser automation pra extrair preços de voos
"""
import asyncio
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Mapeamento de cidades → Códigos de aeroporto IATA
AIRPORT_CODES = {
    "campo grande": "CGR",
    "cuiabá": "CGB",
    "brasília": "BSB",
    "são paulo": "GRU",
    "rio de janeiro": "GIG",
    "belo horizonte": "CNF",
    "salvador": "SSA",
    "recife": "REC",
    "fortaleza": "FOR",
    "manaus": "MAO",
}

async def buscar_preco_google_flights(
    origem_cidade: str,
    destino_cidade: str,
    data_ida: str  # formato DD/MM/YYYY
) -> Optional[Dict]:
    """
    Busca preço real no Google Flights via web scraping

    Args:
        origem_cidade: ex "Campo Grande"
        destino_cidade: ex "Cuiabá"
        data_ida: ex "15/08/2026"

    Returns:
        {
            "preco_por_passageiro": 2272.00,
            "moeda": "BRL",
            "companhias": ["LATAM", "Azul"],
            "tempo_estimado": "6-7 horas",
            "data": "15/08/2026"
        }
    """
    try:
        # Resolve aeroportos
        airport_origem = AIRPORT_CODES.get(origem_cidade.lower(), origem_cidade)
        airport_destino = AIRPORT_CODES.get(destino_cidade.lower(), destino_cidade)

        # Converte data: 15/08/2026 → 20260815
        dia, mes, ano = data_ida.split("/")
        data_param = f"{ano}{mes}{dia}"

        # URL do Google Flights
        url = (
            f"https://www.google.com/flights?hl=pt-BR&curr=BRL"
            f"&fPref=1"  # Preferência de preço
            f"&tfs=CBwQAhomEgoyMDI2MDgxNRoJEgcEAAAAAAAABBoJEgcBAAAAAAAAA"
        )

        # TODO: Implementar scraping via agent-browser ou Selenium
        # Por enquanto, retorna None (fallback para cálculo estimado)
        logger.warning(f"Google Flights scraping não implementado. Usando fallback estimado.")
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar Google Flights: {e}")
        return None


def estimar_preco_aviao(distancia_km: float, data_viagem: str = None) -> Dict:
    """
    Estimativa de preço de avião quando scraping falhar
    Fórmula: Base + (km × taxa)

    Base: R$ 450 (taxa fixa)
    Taxa: R$ 0,60/km (mais barato que carro R$ 1,20)
    """
    base = 450.0
    taxa_km = 0.60
    preco_estimado = base + (distancia_km * taxa_km)

    return {
        "preco_por_passageiro": round(preco_estimado, 2),
        "moeda": "BRL",
        "metodo": "estimativa",
        "formula": f"R$ 450 + ({distancia_km}km × R$ 0,60)",
        "nota": "Usar Google Flights para preço real"
    }
