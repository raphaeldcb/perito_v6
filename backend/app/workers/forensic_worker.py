import asyncio
from sqlalchemy.orm import Session
from app.models.analise_forense import AnaliseForenseResultado
from app.services.forensic_orchestrator import ForensicOrchestrator
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

class ForensicWorker:
    """Background job processor — roda continuamente"""
    
    @staticmethod
    async def run():
        """Processa jobs assincronamente"""
        while True:
            try:
                await asyncio.sleep(5)
                logger.info("Forensic worker running")
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(10)
