"""Dados públicos oficiais para o trabalho pericial — feriados/prazos, CNPJ,
CEP, câmbio/PTAX, FIPE, municípios. Fontes gratuitas (BrasilAPI, BCB, IBGE,
ReceitaWS, ViaCEP, AwesomeAPI, FIPE-parallelum) via services/apis_publicas.py."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.middleware import get_current_user
from app.models import User
from app.services import apis_publicas as pub

router = APIRouter(prefix="/api/v1/publico", tags=["publico"])


def _erro(e: Exception) -> HTTPException:
    if isinstance(e, ValueError):
        return HTTPException(status_code=400, detail=str(e))
    return HTTPException(status_code=502, detail=f"Fonte pública indisponível: {e}")


@router.get("/feriados/{ano}")
async def feriados(ano: int, user: User = Depends(get_current_user)):
    try:
        return pub.feriados(ano)
    except Exception as e:
        raise _erro(e)


@router.get("/prazo")
async def prazo(inicio: date, dias: int, uteis: bool = True,
                user: User = Depends(get_current_user)):
    """Data fatal de prazo processual: ?inicio=2026-07-09&dias=15&uteis=true"""
    try:
        return pub.calcular_prazo(inicio, dias, uteis)
    except Exception as e:
        raise _erro(e)


@router.get("/cnpj/{cnpj}")
async def cnpj(cnpj: str, user: User = Depends(get_current_user)):
    try:
        return pub.consultar_cnpj(cnpj)
    except Exception as e:
        raise _erro(e)


@router.get("/cep/{cep}")
async def cep(cep: str, user: User = Depends(get_current_user)):
    try:
        return pub.consultar_cep(cep)
    except Exception as e:
        raise _erro(e)


@router.get("/municipios/{uf}")
async def municipios(uf: str, user: User = Depends(get_current_user)):
    try:
        return pub.municipios(uf)
    except Exception as e:
        raise _erro(e)


@router.get("/cambio/{par}")
async def cambio(par: str, user: User = Depends(get_current_user)):
    """Cotação em tempo real: /cambio/USD-BRL, /cambio/EUR-BRL, /cambio/BTC-BRL"""
    try:
        return pub.cambio(par)
    except Exception as e:
        raise _erro(e)


@router.get("/ptax")
async def ptax(data: date, user: User = Depends(get_current_user)):
    """PTAX oficial do dólar (BCB) na data: ?data=2026-07-08"""
    try:
        return pub.ptax_dolar(data)
    except Exception as e:
        raise _erro(e)


@router.get("/fipe/marcas")
async def fipe_marcas(tipo: str = "carros", user: User = Depends(get_current_user)):
    try:
        return pub.fipe_marcas(tipo)
    except Exception as e:
        raise _erro(e)


@router.get("/fipe/modelos")
async def fipe_modelos(tipo: str, marca: str, user: User = Depends(get_current_user)):
    try:
        return pub.fipe_modelos(tipo, marca)
    except Exception as e:
        raise _erro(e)


@router.get("/fipe/anos")
async def fipe_anos(tipo: str, marca: str, modelo: str,
                    user: User = Depends(get_current_user)):
    try:
        return pub.fipe_anos(tipo, marca, modelo)
    except Exception as e:
        raise _erro(e)


@router.get("/fipe/valor")
async def fipe_valor(tipo: str, marca: str, modelo: str, ano: str,
                     user: User = Depends(get_current_user)):
    """Valor FIPE oficial — referência para laudos de avaliação de veículos."""
    try:
        return pub.fipe_valor(tipo, marca, modelo, ano)
    except Exception as e:
        raise _erro(e)
