"""Deslocamento v2 — Pedágio automático, terra, múltiplos formatos de localização."""
import os
import math
import json
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from geopy.geocoders import GoogleV3
from geopy.distance import geodesic

# Custos-base (IPC proposta de deslocamento)
CUSTO_KM_ASFALTO = 1.20
CUSTO_KM_TERRA = 3.50
CUSTO_KM_MISTO = 2.35  # Média ponderada

# Coordenadas base (Campo Grande, MS)
COORD_BASE = {"lat": -20.4697, "lon": -55.4033, "cidade": "Campo Grande"}

# Cache de coordenadas para cidades comuns (evita chamadas repetidas à API)
CACHE_CIDADES = {
    "Campo Grande": {"lat": -20.4697, "lon": -55.4033},
    "Dourados": {"lat": -22.2212, "lon": -54.8024},
    "Três Lagoas": {"lat": -20.7548, "lon": -51.6745},
    "Corumbá": {"lat": -19.0030, "lon": -57.6734},
    "Ponta Porã": {"lat": -22.5397, "lon": -55.7178},
    "Naviraí": {"lat": -22.0720, "lon": -55.8341},
    "Nova Andradina": {"lat": -21.9214, "lon": -55.3055},
    "Aquidauana": {"lat": -20.4701, "lon": -55.7906},
    "Maracaju": {"lat": -21.6036, "lon": -55.1668},
    "Sidrolândia": {"lat": -20.9542, "lon": -55.4753},
    "São Paulo": {"lat": -23.5505, "lon": -46.6333},
    "Cuiabá": {"lat": -15.5939, "lon": -56.0973},
    "Curitiba": {"lat": -25.4284, "lon": -49.2733},
    "Brasília": {"lat": -15.7928, "lon": -47.8822},
}

# Pedágio — tarifa aprox. por via (atualizar conforme needed)
PEDAGIO_TARIFAS = {
    "BR-267": 12.50,  # MS/PR
    "BR-262": 8.50,   # MS
    "BR-163": 15.00,  # MS/PR
    "BR-116": 18.00,  # Principal
    "BR-476": 10.00,  # PR
    "default": 10.00,  # Fallback
}


@dataclass
class Coordenada:
    """Estrutura de coordenada lat/lon."""
    latitude: float
    longitude: float

    def to_dict(self):
        return {"lat": self.latitude, "lon": self.longitude}

    def distancia_haversine(self, outra: "Coordenada") -> float:
        """Calcula distância em km via Haversine (terra)."""
        return float(geodesic(
            (self.latitude, self.longitude),
            (outra.latitude, outra.longitude)
        ).kilometers)


class LocalizacaoParser:
    """Parser para múltiplos formatos de localização."""

    @staticmethod
    def parse_endereco(endereco: str, geocoder_key: Optional[str] = None) -> Optional[Coordenada]:
        """Parse endereço → coordenadas via Google Geocoding.

        Args:
            endereco: String com endereço (ex: "Rua das Flores, 123, Campo Grande, MS")
            geocoder_key: API key do Google Geocoding (opcional)

        Returns:
            Coordenada ou None se falhar
        """
        try:
            # Usar chave passada, ou ler de .env
            key = geocoder_key or os.environ.get("GOOGLE_MAPS_API_KEY")
            if key:
                geocoder = GoogleV3(api_key=key)
            else:
                geocoder = GoogleV3()  # Rate-limited, use key em prod

            location = geocoder.geocode(endereco, timeout=5)
            if location:
                return Coordenada(location.latitude, location.longitude)
        except Exception as e:
            print(f"Erro ao geocodificar '{endereco}': {e}")
        return None

    @staticmethod
    def parse_latlon(lat: float, lon: float) -> Coordenada:
        """Parse lat/lon diretos → Coordenada."""
        return Coordenada(float(lat), float(lon))

    @staticmethod
    def parse_cep(cep: str, geocoder_key: Optional[str] = None) -> Optional[Coordenada]:
        """Parse CEP → coordenadas via Google Geocoding."""
        # Remove formatação comum de CEP (12345-678 → 12345678)
        cep_limpo = cep.replace("-", "").replace(".", "").strip()
        return LocalizacaoParser.parse_endereco(f"CEP {cep_limpo}, Brasil", geocoder_key)

    @staticmethod
    def parse_kml(conteudo_kml: str) -> List[Coordenada]:
        """Parse arquivo KML → lista de coordenadas.

        Extrai todos os pontos <Placemark> com <Point><coordinates>.
        """
        coords = []
        try:
            root = ET.fromstring(conteudo_kml)
            # KML usa namespace
            ns = {"kml": "http://www.opengis.net/kml/2.2"}
            for placemark in root.findall(".//kml:Placemark", ns):
                point = placemark.find("kml:Point/kml:coordinates", ns)
                if point is not None and point.text:
                    # KML: lon,lat,alt (separado por vírgula)
                    parts = point.text.strip().split(",")
                    if len(parts) >= 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        coords.append(Coordenada(lat, lon))
        except Exception as e:
            print(f"Erro ao parsear KML: {e}")
        return coords

    @staticmethod
    def parse_geojson(conteudo_json: str) -> List[Coordenada]:
        """Parse arquivo GeoJSON → lista de coordenadas.

        Extrai coordenadas de features (suporta Point, LineString, Polygon).
        """
        coords = []
        try:
            data = json.loads(conteudo_json)
            if data.get("type") == "FeatureCollection":
                features = data.get("features", [])
            else:
                features = [data]

            for feature in features:
                geom = feature.get("geometry", {})
                if geom.get("type") == "Point":
                    lon, lat = geom.get("coordinates", [None, None])
                    if lon is not None and lat is not None:
                        coords.append(Coordenada(lat, lon))
                elif geom.get("type") == "LineString":
                    for lon, lat in geom.get("coordinates", []):
                        coords.append(Coordenada(lat, lon))
                elif geom.get("type") == "Polygon":
                    # Pega primeiro e último ponto do primeiro ring
                    for lon, lat in geom.get("coordinates", [[]])[0]:
                        coords.append(Coordenada(lat, lon))
        except Exception as e:
            print(f"Erro ao parsear GeoJSON: {e}")
        return coords


class DeslocamentoCalculator:
    """Calculador principal de deslocamento com múltiplas features."""

    def __init__(self, geocoder_key: Optional[str] = None):
        self.geocoder_key = geocoder_key
        self.parser = LocalizacaoParser()

    def calcular_deslocamento(
        self,
        origem: str,
        destino: str,
        tipo_origem: str = "endereco",  # endereco | latlon | cep
        tipo_destino: str = "endereco",
        tipo_deslocamento: str = "rodovia",  # rodovia | terra | misto
        incluir_pedagio: bool = True,
        pedagio_manual: Optional[float] = None,
        ida_volta: bool = True,
        distancia_manual: Optional[float] = None,
    ) -> Dict:
        """Calcula deslocamento completo com pedágio.

        Args:
            origem: Descrição ou coordenadas de origem
            destino: Descrição ou coordenadas de destino
            tipo_origem: Formato de origem
            tipo_destino: Formato de destino
            tipo_deslocamento: rodovia | terra | misto
            incluir_pedagio: Se True, busca pedágio automático
            pedagio_manual: Valor manual de pedágio (fallback)
            ida_volta: Se True, multiplica por 2
            distancia_manual: Se fornecida, usa esta distância em vez de calcular

        Returns:
            Dict com cálculo completo
        """
        # 1. Parse de coordenadas
        coord_origem = self._parse_localizacao(origem, tipo_origem)
        coord_destino = self._parse_localizacao(destino, tipo_destino)

        if not coord_origem or not coord_destino:
            return {
                "erro": "Não foi possível resolver as coordenadas",
                "origem": origem,
                "destino": destino,
            }

        # 2. Calcula distância
        if distancia_manual:
            distancia_km = float(distancia_manual)
        else:
            if tipo_deslocamento == "terra":
                # Terra: usa Haversine (linha reta)
                distancia_km = coord_origem.distancia_haversine(coord_destino)
            else:
                # Rodovia/Misto: usa Haversine (simplificado; prod usa Google Distance Matrix)
                distancia_km = coord_origem.distancia_haversine(coord_destino) * 1.15  # Ajuste rodoviário

        # 3. Pedágio
        pedagio_ida = 0.0
        if incluir_pedagio:
            if pedagio_manual is not None:
                pedagio_ida = float(pedagio_manual)
            else:
                # Estimativa automática baseada em tipo e distância
                pedagio_ida = self._estimar_pedagio(tipo_deslocamento, distancia_km)

        # 4. Tarifa por km
        if tipo_deslocamento == "rodovia":
            custo_km = CUSTO_KM_ASFALTO
        elif tipo_deslocamento == "terra":
            custo_km = CUSTO_KM_TERRA
        else:  # misto
            custo_km = CUSTO_KM_MISTO

        # 5. Cálculo final
        fator = 2 if ida_volta else 1
        km_total = distancia_km * fator
        custo_rodagem = km_total * custo_km
        pedagio_total = pedagio_ida * fator
        total_deslocamento = custo_rodagem + pedagio_total

        return {
            "sucesso": True,
            "origem": {
                "descricao": origem,
                "tipo": tipo_origem,
                "lat": round(coord_origem.latitude, 6),
                "lon": round(coord_origem.longitude, 6),
            },
            "destino": {
                "descricao": destino,
                "tipo": tipo_destino,
                "lat": round(coord_destino.latitude, 6),
                "lon": round(coord_destino.longitude, 6),
            },
            "distancia_km": round(distancia_km, 2),
            "km_total": round(km_total, 2),
            "tipo_deslocamento": tipo_deslocamento,
            "custo_km": round(custo_km, 2),
            "custo_rodagem": round(custo_rodagem, 2),
            "pedagio_ida": round(pedagio_ida, 2),
            "pedagio_total": round(pedagio_total, 2),
            "ida_volta": ida_volta,
            "total_deslocamento": round(total_deslocamento, 2),
        }

    def calcular_multiplos_pontos(
        self,
        pontos: List[Dict],  # [{"descricao": "...", "tipo": "endereco", "valor": "..."}]
        tipo_deslocamento: str = "rodovia",
        incluir_pedagio: bool = True,
        ida_volta: bool = False,  # Em múltiplos pontos, geralmente é ponto a ponto
    ) -> Dict:
        """Calcula deslocamento visitando múltiplos pontos (rota).

        Args:
            pontos: Lista de pontos com descricao, tipo, valor
            tipo_deslocamento: rodovia | terra | misto
            incluir_pedagio: Se True, busca pedágio automático
            ida_volta: Se True, volta ao ponto inicial ao final

        Returns:
            Dict com cálculo de rota completa
        """
        if len(pontos) < 2:
            return {"erro": "Mínimo 2 pontos requerido"}

        coordenadas = []
        for ponto in pontos:
            coord = self._parse_localizacao(ponto["valor"], ponto.get("tipo", "endereco"))
            if not coord:
                return {"erro": f"Não resolveu: {ponto['descricao']}"}
            coordenadas.append((ponto["descricao"], coord))

        # Calcula distância entre pontos consecutivos
        distancia_total = 0.0
        pedagio_total = 0.0
        etapas = []

        for i in range(len(coordenadas) - 1):
            desc_origem, coord_origem = coordenadas[i]
            desc_destino, coord_destino = coordenadas[i + 1]

            dist = coord_origem.distancia_haversine(coord_destino)
            if tipo_deslocamento == "rodovia":
                dist *= 1.15  # Ajuste rodoviário

            distancia_total += dist

            # Pedágio por etapa
            pedag = self._estimar_pedagio(tipo_deslocamento, dist) if incluir_pedagio else 0.0
            pedagio_total += pedag

            etapas.append({
                "de": desc_origem,
                "para": desc_destino,
                "distancia_km": round(dist, 2),
                "pedagio": round(pedag, 2),
            })

        # Se volta ao ponto inicial
        if ida_volta:
            dist_volta = coordenadas[-1][1].distancia_haversine(coordenadas[0][1])
            if tipo_deslocamento == "rodovia":
                dist_volta *= 1.15
            distancia_total += dist_volta
            pedagio_volta = self._estimar_pedagio(tipo_deslocamento, dist_volta) if incluir_pedagio else 0.0
            pedagio_total += pedagio_volta
            etapas.append({
                "de": coordenadas[-1][0],
                "para": coordenadas[0][0],
                "distancia_km": round(dist_volta, 2),
                "pedagio": round(pedagio_volta, 2),
            })

        # Tarifa
        custo_km = (CUSTO_KM_ASFALTO if tipo_deslocamento == "rodovia"
                   else CUSTO_KM_TERRA if tipo_deslocamento == "terra"
                   else CUSTO_KM_MISTO)
        custo_rodagem = distancia_total * custo_km
        total = custo_rodagem + pedagio_total

        return {
            "sucesso": True,
            "tipo_deslocamento": tipo_deslocamento,
            "distancia_total_km": round(distancia_total, 2),
            "custo_km": round(custo_km, 2),
            "custo_rodagem": round(custo_rodagem, 2),
            "pedagio_total": round(pedagio_total, 2),
            "total_deslocamento": round(total, 2),
            "num_pontos": len(coordenadas),
            "ida_volta": ida_volta,
            "etapas": etapas,
        }

    def gerar_preview_mapa(
        self,
        origem: str,
        destino: str,
        tipo_origem: str = "endereco",
        tipo_destino: str = "endereco",
    ) -> Optional[str]:
        """Gera HTML com mapa folium (origem → destino).

        Returns:
            HTML string ou None se falhar
        """
        try:
            import folium
            from io import StringIO
        except ImportError:
            return None

        coord_origem = self._parse_localizacao(origem, tipo_origem)
        coord_destino = self._parse_localizacao(destino, tipo_destino)

        if not coord_origem or not coord_destino:
            return None

        # Centro do mapa (ponto médio)
        lat_centro = (coord_origem.latitude + coord_destino.latitude) / 2
        lon_centro = (coord_origem.longitude + coord_destino.longitude) / 2

        # Mapa
        mapa = folium.Map(
            location=[lat_centro, lon_centro],
            zoom_start=7,
            tiles="OpenStreetMap",
        )

        # Marcadores
        folium.Marker(
            location=[coord_origem.latitude, coord_origem.longitude],
            popup="Origem",
            icon=folium.Icon(color="green"),
        ).add_to(mapa)

        folium.Marker(
            location=[coord_destino.latitude, coord_destino.longitude],
            popup="Destino",
            icon=folium.Icon(color="red"),
        ).add_to(mapa)

        # Linha conectando
        folium.PolyLine(
            locations=[
                [coord_origem.latitude, coord_origem.longitude],
                [coord_destino.latitude, coord_destino.longitude],
            ],
            color="blue",
            weight=2,
        ).add_to(mapa)

        # Retorna HTML
        output = StringIO()
        mapa.save(output, close_file=False)
        return output.getvalue()

    def _parse_localizacao(
        self,
        valor: str,
        tipo: str,
    ) -> Optional[Coordenada]:
        """Helper interno: parse valor conforme tipo."""
        if tipo == "endereco":
            # Verifica cache primeiro
            if valor in CACHE_CIDADES:
                c = CACHE_CIDADES[valor]
                return Coordenada(c["lat"], c["lon"])
            return self.parser.parse_endereco(valor, self.geocoder_key)

        elif tipo == "latlon":
            # Formato: "lat,lon" ou "lat lon"
            sep = "," if "," in valor else " "
            parts = valor.split(sep)
            if len(parts) == 2:
                try:
                    return Coordenada(float(parts[0]), float(parts[1]))
                except ValueError:
                    pass

        elif tipo == "cep":
            return self.parser.parse_cep(valor, self.geocoder_key)

        return None

    def _estimar_pedagio(self, tipo_deslocamento: str, distancia_km: float) -> float:
        """Estimativa simplificada de pedágio baseada em tipo e distância."""
        if tipo_deslocamento == "terra":
            return 0.0  # Sem pedágio em terra

        # Rodovia/Misto: R$ 10-15 por 100km (simplificado)
        if distancia_km < 50:
            return 0.0
        elif distancia_km < 100:
            return 10.0
        elif distancia_km < 200:
            return 20.0
        elif distancia_km < 400:
            return 40.0
        else:
            return 50.0 + (distancia_km - 400) * 0.1
