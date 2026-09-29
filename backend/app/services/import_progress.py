"""
Progress tracking para importação de dados com deduplicação.
Detecta duplicatas por similaridade de nome (Levenshtein distance).
"""
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from app.models import Processo, Intimacao, Laudo

@dataclass
class ImportProgress:
    """Rastreia progresso da importação com WebSocket/SSE."""
    current: int = 0
    total: int = 0
    status: str = "iniciando"
    mensagem: str = ""
    etapa: str = ""

    @property
    def percentual(self) -> float:
        return (self.current / self.total * 100) if self.total > 0 else 0

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "total": self.total,
            "percentual": round(self.percentual, 1),
            "status": self.status,
            "mensagem": self.mensagem,
            "etapa": self.etapa
        }

class DuplicataDetector:
    """Detecta registros duplicados por similaridade de nome."""

    THRESHOLD = 0.85  # 85% de similaridade = provável duplicata

    @staticmethod
    def similaridade(s1: str, s2: str) -> float:
        """Calcula similaridade entre dois strings (0-1)."""
        if not s1 or not s2:
            return 0.0
        s1_clean = s1.lower().strip()
        s2_clean = s2.lower().strip()
        return SequenceMatcher(None, s1_clean, s2_clean).ratio()

    @staticmethod
    def buscar_duplicatas_processo(db: Session, numero_cnj: str, titulo: str) -> List[Dict[str, Any]]:
        """Busca possíveis duplicatas de processo."""
        candidatos = []

        # Buscar por número CNJ exato
        if numero_cnj:
            processo_exato = db.query(Processo).filter(
                Processo.numero_cnj == numero_cnj
            ).first()
            if processo_exato:
                candidatos.append({
                    "id": processo_exato.id,
                    "tipo": "processo",
                    "numero_cnj": processo_exato.numero_cnj,
                    "titulo": processo_exato.titulo,
                    "similaridade": 1.0,
                    "motivo": "Match exato no número CNJ"
                })

        # Buscar por titulo similar (se houver)
        if titulo:
            processos = db.query(Processo).limit(100).all()
            for p in processos:
                sim = DuplicataDetector.similaridade(titulo, p.titulo or "")
                if sim >= DuplicataDetector.THRESHOLD:
                    candidatos.append({
                        "id": p.id,
                        "tipo": "processo",
                        "numero_cnj": p.numero_cnj,
                        "titulo": p.titulo,
                        "similaridade": round(sim, 3),
                        "motivo": f"Título similar ({int(sim*100)}%)"
                    })

        return sorted(candidatos, key=lambda x: x["similaridade"], reverse=True)

    @staticmethod
    def buscar_duplicatas_intimacao(db: Session, numero_processo: str, data: str) -> List[Dict[str, Any]]:
        """Busca possíveis duplicatas de intimação."""
        candidatos = []

        if numero_processo:
            intimacoes = db.query(Intimacao).filter(
                Intimacao.numero_processo == numero_processo
            ).all()

            for i in intimacoes:
                razoes = []
                if data and i.data_intimacao and str(i.data_intimacao) == data:
                    razoes.append("data exata")

                if razoes:
                    candidatos.append({
                        "id": i.id,
                        "tipo": "intimacao",
                        "numero_processo": i.numero_processo,
                        "data": str(i.data_intimacao),
                        "similaridade": 1.0,
                        "motivo": ", ".join(razoes)
                    })

        return candidatos

async def validar_mapeamento_csv(
    csv_data: List[Dict[str, str]],
    db: Session,
    progress_callback = None
) -> Dict[str, Any]:
    """
    Valida dados CSV antes de importar.
    Retorna: dados validados + duplicatas detectadas + campos mapeados.
    """
    progress = ImportProgress(total=len(csv_data))

    validados = []
    duplicatas_encontradas = []
    campos_mapeados = {}

    for idx, linha in enumerate(csv_data):
        progress.current = idx + 1
        progress.etapa = f"Validando linha {idx + 1}/{len(csv_data)}"

        if progress_callback:
            await progress_callback(progress.to_dict())

        # Detectar duplicatas para processos
        if "numero_cnj" in linha or "titulo" in linha:
            duplicatas = DuplicataDetector.buscar_duplicatas_processo(
                db,
                numero_cnj=linha.get("numero_cnj"),
                titulo=linha.get("titulo")
            )

            if duplicatas:
                duplicatas_encontradas.append({
                    "linha": idx + 1,
                    "dados": linha,
                    "duplicatas": duplicatas
                })
            else:
                validados.append({"linha": idx + 1, "dados": linha})
        else:
            validados.append({"linha": idx + 1, "dados": linha})

        # Rastrear campos mapeados
        for chave in linha.keys():
            campos_mapeados[chave] = campos_mapeados.get(chave, 0) + 1

    progress.status = "concluído"
    progress.mensagem = f"{len(validados)} linhas OK, {len(duplicatas_encontradas)} duplicatas detectadas"

    if progress_callback:
        await progress_callback(progress.to_dict())

    return {
        "total_linhas": len(csv_data),
        "validadas": len(validados),
        "duplicatas_detectadas": len(duplicatas_encontradas),
        "percentual_valido": round(len(validados) / len(csv_data) * 100, 1),
        "dados_validados": validados,
        "duplicatas": duplicatas_encontradas,
        "campos_mapeados": campos_mapeados
    }
