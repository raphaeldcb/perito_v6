"""Fallback para índice IPCA 04/2011-05/2012"""
from datetime import date, datetime

FALLBACK_IPCA = {
    "2011-04": 0.77, "2011-05": 0.47, "2011-06": 0.15, "2011-07": 0.26,
    "2011-08": 0.62, "2011-09": 0.52, "2011-10": 1.17, "2011-11": 0.52,
    "2011-12": 0.50, "2012-01": 0.56, "2012-02": 0.45, "2012-03": 0.21,
    "2012-04": 0.64, "2012-05": 0.36
}

def serie_ipca_2011_2012(data_ini: date, data_fim: date) -> dict:
    """Retorna IPCA fallback para 04/2011-05/2012"""
    resultado = {}
    for chave, valor in FALLBACK_IPCA.items():
        try:
            d = datetime.strptime(chave, "%Y-%m").date()
            if data_ini <= d <= data_fim:
                resultado[chave] = valor
        except:
            pass
    return resultado
