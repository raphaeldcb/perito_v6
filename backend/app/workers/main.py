"""Entrypoint único dos workers (serviço 'worker' no docker-compose).

Ciclo a cada WORKER_INTERVALO_MIN minutos:
  1. Captura emails de intimação (EWS) — se credenciais configuradas
  2. Analisa intimações pendentes (Ollama/Qwen)
  3. Enfileira protocolo de cartões aprovados

Cada passo é isolado: uma falha não derruba o loop, mas é logada com traceback.
"""
import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("worker")

INTERVALO_MIN = int(os.environ.get("WORKER_INTERVALO_MIN", "10"))


def ciclo():
    from app.workers import monitor_emails, analise_qwen, protocolo_automatico

    try:
        n = monitor_emails.processar_caixa_entrada()
        if n:
            logger.info(f"Emails processados: {n}")
    except Exception:
        logger.exception("Falha no monitor de emails")

    try:
        n = analise_qwen.processar_intimacoes_pendentes()
        if n:
            logger.info(f"Intimações analisadas: {n}")
    except Exception:
        logger.exception("Falha na análise de intimações")

    try:
        n = protocolo_automatico.enfileirar_cartoes_aprovados()
        if n:
            logger.info(f"Cartões enfileirados para protocolo: {n}")
    except Exception:
        logger.exception("Falha no enfileiramento de protocolos")

    # DESABILITADO: Busca de intimações ESAJ — comentado até nova ordem (23/07/26)
    # try:
    #     n = enfileirar_busca_esaj()
    #     if n:
    #         logger.info("Busca de intimações ESAJ enfileirada para o agente Mac")
    # except Exception:
    #     logger.exception("Falha ao enfileirar busca ESAJ")

    # Índices do Banco Central — atualiza no BD só se vencidos (>10 dias)
    try:
        from app.services import indices_bcb
        from app.services.database import SessionLocal
        db = SessionLocal()
        try:
            indices_bcb.atualizar_todos(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao atualizar índices do BCB")

    # Diário Oficial (DJEN) — CAPTAÇÃO automática: enfileira análise Qwen das
    # publicações novas → vira Oportunidade ranqueada (não cria Processo).
    if os.environ.get("CAPTACAO_AUTOMATICA", "1") == "1":
        try:
            from app.services import diario_djen
            from app.services.database import SessionLocal
            db = SessionLocal()
            try:
                n = diario_djen.captar_automatico(db)
                if n:
                    logger.info(f"Captação DJEN: {n} enfileiradas p/ Qwen")
            finally:
                db.close()
        except Exception:
            logger.exception("Falha na captação DJEN")
    # (tracking de casos próprios por consultar_e_salvar fica desligado por padrão —
    #  reativar com DIARIO_AUTOMATICO=1 usando termos do nome do escritório)
    elif os.environ.get("DIARIO_AUTOMATICO", "0") == "1":
        try:
            from app.services import diario_djen
            from app.services.database import SessionLocal
            db = SessionLocal()
            try:
                n = diario_djen.consultar_e_salvar(db)
                if n:
                    logger.info(f"DJEN: {n} publicações novas")
            finally:
                db.close()
        except Exception:
            logger.exception("Falha na busca do DJEN")

    try:
        from app.workers import relatorios
        if relatorios.enviar_relatorio_diario():
            logger.info("Relatório diário enviado")
    except Exception:
        logger.exception("Falha no relatório diário")


def enfileirar_busca_esaj() -> int:
    """Enfileira um job para o agente Mac ir ao ESAJ puxar a fila de intimações
    pendentes (login CPF/senha+2FA). Só 1 por vez e no máximo 1 por hora."""
    from datetime import datetime, timedelta
    from app.models import Job
    from app.services.database import SessionLocal

    if os.environ.get("ESAJ_BUSCA_AUTOMATICA", "1") != "1":
        return 0

    # Só nos horários determinados pelo TJMS: 6h e 20h (horário de MS = UTC-4).
    # Fora disso não acessa o eSAJ — corrige o "acesso fora do horário" (antes 1x/hora).
    if (datetime.utcnow() - timedelta(hours=4)).hour not in (6, 20):
        return 0

    db = SessionLocal()
    try:
        # já tem um aberto? não duplica
        aberto = db.query(Job).filter(
            Job.tipo == "esaj_intimacoes", Job.status.in_(["na_fila", "processando"])
        ).first()
        if aberto:
            return 0
        # último concluído há menos de 1h? espera
        ultimo = db.query(Job).filter(Job.tipo == "esaj_intimacoes").order_by(Job.id.desc()).first()
        if ultimo and ultimo.created_at and (datetime.utcnow() - ultimo.created_at) < timedelta(hours=1):
            return 0
        db.add(Job(tipo="esaj_intimacoes", payload={"tribunal": "TJMS"}, status="na_fila"))
        db.commit()
        return 1
    finally:
        db.close()


def main():
    logger.info(f"🔄 Worker iniciado — ciclo a cada {INTERVALO_MIN} min")
    # Espera o backend criar as tabelas/seed antes do primeiro ciclo
    time.sleep(20)
    while True:
        ciclo()
        time.sleep(INTERVALO_MIN * 60)


if __name__ == "__main__":
    main()
