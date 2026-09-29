"""
Endpoint para receber eventos do AssistProduction Agent (Windows).
- Screenshots
- Atividade do usuário
- Status da máquina
"""
from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import base64
from pathlib import Path

from app.services.database import SessionLocal

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class EventoAgente(BaseModel):
    tipo: str  # "screenshot", "atividade", "status", "erro"
    timestamp: datetime
    dados: Dict[str, Any]
    screenshot_base64: Optional[str] = None


def verificar_agente(x_agent_key: str = Header(None)):
    """Verifica se a chave do agente é válida"""
    from app.core.config import settings
    if x_agent_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Chave de agente inválida")
    return x_agent_key


@router.post("/events")
def receber_evento(
    evento: EventoAgente,
    agent_key: str = Depends(verificar_agente),
    db: Session = Depends(SessionLocal)
):
    """Recebe evento do agente AssistProduction"""
    try:
        # Se tiver screenshot, salvar em disco
        if evento.screenshot_base64:
            pasta = Path("/tmp/assistprod-screenshots")
            pasta.mkdir(exist_ok=True)

            img_data = base64.b64decode(evento.screenshot_base64)
            filename = f"{evento.timestamp.isoformat().replace(':', '-')}.png"
            filepath = pasta / filename

            with open(filepath, "wb") as f:
                f.write(img_data)

            evento.dados["screenshot_path"] = str(filepath)

        # Log do evento
        import logging
        logger = logging.getLogger("agent")
        logger.info(f"📸 Evento {evento.tipo}: {evento.dados}")

        return {
            "status": "recebido",
            "timestamp": datetime.utcnow().isoformat(),
            "tipo": evento.tipo
        }

    except Exception as e:
        return {
            "status": "erro",
            "erro": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/status")
def status_agente(
    agent_key: str = Depends(verificar_agente)
):
    """Retorna status do servidor de eventos"""
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "versao": "1.0.0"
    }


@router.post("/register")
def registrar_agente(
    hostname: str,
    usuario: str,
    agent_key: str = Depends(verificar_agente)
):
    """Registra agente na rede"""
    import logging
    logger = logging.getLogger("agent")
    logger.info(f"✅ Agente registrado: {hostname} ({usuario})")

    return {
        "status": "registrado",
        "timestamp": datetime.utcnow().isoformat(),
        "id_agente": f"{hostname}_{usuario}"
    }
