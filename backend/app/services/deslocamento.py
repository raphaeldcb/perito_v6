"""Cálculo de deslocamento/rota — custo por km + pedágio + ida/volta.

Custos-base (da proposta de deslocamento IPC): asfalto R$1,20/km, chão R$3,50/km.
Distâncias a partir de Campo Grande/MS (aprox., rodoviário) para conveniência;
o perito pode digitar a distância manualmente para qualquer origem/destino.
"""
CUSTO_KM_ASFALTO = 1.20
CUSTO_KM_CHAO = 3.50

# distância rodoviária aprox. de Campo Grande (km) — MS + capitais próximas
DISTANCIAS_CG = {
    "Dourados": 225, "Três Lagoas": 338, "Corumbá": 417, "Ponta Porã": 322,
    "Naviraí": 372, "Nova Andradina": 300, "Aquidauana": 130, "Maracaju": 158,
    "Sidrolândia": 70, "Coxim": 253, "Paranaíba": 439, "Amambai": 386,
    "Rio Brilhante": 162, "Bonito": 296, "Jardim": 238, "Miranda": 200,
    "Chapadão do Sul": 329, "São Gabriel do Oeste": 136, "Bataguassu": 330,
    "Cassilândia": 456, "Anastácio": 133, "Ivinhema": 293, "Bela Vista": 320,
    "São Paulo": 1014, "Cuiabá": 694, "Goiânia": 838, "Brasília": 1134,
    "Curitiba": 991, "Presidente Prudente": 452,
}


def cidades() -> list[dict]:
    return sorted([{"cidade": c, "distancia_km": d} for c, d in DISTANCIAS_CG.items()],
                  key=lambda x: x["cidade"])


def calcular(distancia_km: float, tipo_via: str = "asfalto", pedagios: float = 0.0,
             ida_volta: bool = True, custo_km: float = None) -> dict:
    if custo_km is None:
        custo_km = CUSTO_KM_ASFALTO if tipo_via == "asfalto" else CUSTO_KM_CHAO
    fator = 2 if ida_volta else 1
    km_total = distancia_km * fator
    custo_rodagem = km_total * custo_km
    total = custo_rodagem + pedagios * fator
    return {
        "distancia_km": round(distancia_km, 1),
        "ida_volta": ida_volta,
        "km_total": round(km_total, 1),
        "custo_km": round(custo_km, 2),
        "custo_rodagem": round(custo_rodagem, 2),
        "pedagios": round(pedagios * fator, 2),
        "total": round(total, 2),
    }
