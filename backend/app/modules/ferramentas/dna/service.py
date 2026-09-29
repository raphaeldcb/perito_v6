"""
DNA Module Service Layer — Business logic for DNA analysis.

Handles:
- Static data retrieval (tipos-parentesco, enquadramentos)
- Aggregations and calculations
- Database queries
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import ParticipanteDNA, EnquadramentoDNA, Processo


def get_tipos_parentesco() -> Dict[str, List[Dict[str, str]]]:
    """Retorna lista de tipos de parentesco DNA para dropdown (público)."""
    return {
        "tipos": [
            {"id": "CRI", "label": "Criança/Investigante"},
            {"id": "MA1", "label": "Mãe"},
            {"id": "MA2", "label": "Mãe dos SMIs"},
            {"id": "SP1", "label": "Suposto Pai 1"},
            {"id": "SP2", "label": "Suposto Pai 2"},
            {"id": "SP3", "label": "Suposto Pai 3"},
            {"id": "SMI1", "label": "Suposto Meio-Irmão 1 (com MA2)"},
            {"id": "SMI2", "label": "Suposto Meio-Irmão 2 (com MA2)"},
            {"id": "SMI3", "label": "Suposto Meio-Irmão 3 (com MA2)"},
            {"id": "ST1", "label": "Suposto Tio Paterno 1"},
            {"id": "ST2", "label": "Suposto Tio Paterno 2"},
            {"id": "ST3", "label": "Suposto Tio Paterno 3"},
            {"id": "AGM", "label": "Suposto Avó Materna"},
            {"id": "AGF", "label": "Suposto Avô Paterno"},
            {"id": "OUTRO", "label": "Outro"},
        ]
    }


def get_enquadramentos() -> Dict[str, List[Dict[str, Any]]]:
    """Retorna lista de enquadramentos DNA para dropdown."""
    return {
        "enquadramentos": [
            # PATERNIDADE DIRETA
            {
                "id": "PD0101",
                "codigo": "PD0101",
                "descricao": "Mãe, criança e suposto pai",
                "categoria": "Paternidade Direta",
                "valor_particular": 800.00,
                "valor_judicial": 600.00,
            },
            {
                "id": "PD0201",
                "codigo": "PD0201",
                "descricao": "Criança e suposto pai",
                "categoria": "Paternidade Direta",
                "valor_particular": 800.00,
                "valor_judicial": 600.00,
            },
            # RECONSTRUÇÃO DIRETA
            {
                "id": "RD0301",
                "codigo": "RD0301",
                "descricao": "Mãe, criança e supostos avós",
                "categoria": "Reconstrução Direta",
                "valor_particular": 1500.00,
                "valor_judicial": 1200.00,
            },
            {
                "id": "RD0302",
                "codigo": "RD0302",
                "descricao": "Criança e supostos avós",
                "categoria": "Reconstrução Direta",
                "valor_particular": 2100.00,
                "valor_judicial": 1800.00,
            },
            {
                "id": "RD0501",
                "codigo": "RD0501",
                "descricao": "Mãe, criança e 3 supostos meios-irmãos com MA2",
                "categoria": "Reconstrução Direta",
                "valor_particular": 2700.00,
                "valor_judicial": 2400.00,
            },
            {
                "id": "RD0502",
                "codigo": "RD0502",
                "descricao": "Mãe, criança e 2 supostos meios-irmãos com MA2",
                "categoria": "Reconstrução Direta",
                "valor_particular": 3200.00,
                "valor_judicial": 3000.00,
            },
            {
                "id": "RD0503",
                "codigo": "RD0503",
                "descricao": "Mãe, criança e 1 suposto meio-irmão com MA2",
                "categoria": "Reconstrução Direta",
                "valor_particular": 3800.00,
                "valor_judicial": 3200.00,
            },
            # RECONSTRUÇÃO INDIRETA
            {
                "id": "RI0401",
                "codigo": "RI0401",
                "descricao": "Mãe, criança e 3 supostos tios paternos",
                "categoria": "Reconstrução Indireta",
                "valor_particular": 2700.00,
                "valor_judicial": 2400.00,
            },
            {
                "id": "RI0402",
                "codigo": "RI0402",
                "descricao": "Mãe, criança e 2 supostos tios paternos",
                "categoria": "Reconstrução Indireta",
                "valor_particular": 3200.00,
                "valor_judicial": 3000.00,
            },
            {
                "id": "RI0403",
                "codigo": "RI0403",
                "descricao": "Mãe, criança e 1 suposto tio paterno com 1 dos avós",
                "categoria": "Reconstrução Indireta",
                "valor_particular": 3800.00,
                "valor_judicial": 3200.00,
            },
        ]
    }


def calcular_valor_dna(processo_id: int, db: Session) -> Dict[str, Any]:
    """Calcula valor total DNA (judicial + particular) para integração financeira."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        return {"error": "Processo não encontrado"}

    enquadramentos = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.processo_id == processo_id
    ).all()

    valor_total_judicial = sum(e.valor_judicial or 0 for e in enquadramentos)
    valor_total_particular = sum(e.valor_particular or 0 for e in enquadramentos)

    return {
        "processo_id": processo_id,
        "quantidade_enquadramentos": len(enquadramentos),
        "valor_judicial": valor_total_judicial,
        "valor_particular": valor_total_particular,
        "enquadramentos": [
            {
                "codigo": e.codigo,
                "descricao": e.descricao,
                "valor_judicial": e.valor_judicial,
                "valor_particular": e.valor_particular,
                "resultado": e.resultado,
                "probabilidade": e.probabilidade
            }
            for e in enquadramentos
        ]
    }


def sumario_dna(processo_id: int, db: Session) -> Dict[str, Any]:
    """Retorna sumário DNA para exibição no andamento do processo."""
    processo = db.query(Processo).filter(Processo.id == processo_id).first()
    if not processo:
        return {"error": "Processo não encontrado"}

    participantes = db.query(ParticipanteDNA).filter(
        ParticipanteDNA.processo_id == processo_id
    ).all()

    enquadramentos = db.query(EnquadramentoDNA).filter(
        EnquadramentoDNA.processo_id == processo_id
    ).all()

    requerentes = [p.nome for p in participantes if p.requerente]
    requeridos = [p.nome for p in participantes if p.requerido]

    resultado_final = None
    if enquadramentos:
        resultado_final = enquadramentos[0].resultado
        if resultado_final == "INCLUSÃO" and enquadramentos[0].probabilidade:
            resultado_final = f"INCLUSÃO ({enquadramentos[0].probabilidade}%)"

    return {
        "processo_id": processo_id,
        "total_participantes": len(participantes),
        "requerentes": requerentes,
        "requeridos": requeridos,
        "enquadramentos_selecionados": len(enquadramentos),
        "resultado_dna": resultado_final,
        "status": "Aguardando resultado" if not resultado_final else "Resultado disponível"
    }
