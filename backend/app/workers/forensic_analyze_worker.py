"""
Worker: Análise Forense em Background
Executa FakeDetectorCombo + Gera PDF + Salva no BD
"""
import logging
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import create_engine

log = logging.getLogger("forensic_worker")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - forensic_worker - %(levelname)s - %(message)s'))
log.addHandler(handler)

# Adicionar scripts ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from fake_detector_combo import FakeDetectorCombo
except ImportError:
    log.warning("FakeDetectorCombo não disponível")
    FakeDetectorCombo = None


def process_forensic_laudo(db: Session, laudo_id: int, arquivo_path: str) -> bool:
    """
    Processa laudo forense: análise + PDF + armazenamento.

    Args:
        db: Sessão SQLAlchemy
        laudo_id: ID do laudo no BD
        arquivo_path: Caminho temporário do arquivo

    Returns:
        bool: True se sucesso, False se erro
    """
    from app.models import LaudoForense
    from app.services.forensic_laudo_generator import LaudoForenseGenerator

    try:
        # 1. Carregar laudo
        laudo = db.query(LaudoForense).filter(LaudoForense.id == laudo_id).first()
        if not laudo:
            log.error(f"Laudo {laudo_id} não encontrado")
            return False

        log.info(f"[{laudo.numero_laudo}] Iniciando análise...")

        # 2. Executar análise (se FakeDetectorCombo disponível)
        resultados_apis = []
        veredicto = "REVISAR"
        authenticity_score = 0.0
        consensus = 0.0

        if FakeDetectorCombo and Path(arquivo_path).exists():
            try:
                detector = FakeDetectorCombo()
                resultado = asyncio.run(detector.analisar_combo(arquivo_path, usar_apis=None))

                log.info(f"[{laudo.numero_laudo}] Análise concluída: {resultado.status}")

                # Extrair dados
                veredicto = resultado.status  # APROVADO/REJEITADO/REVISAR
                authenticity_score = resultado.confianca_media
                consensus = resultado.consensus_pct

                # Resultados por API
                if hasattr(resultado, 'resultados_apis') and resultado.resultados_apis:
                    for r in resultado.resultados_apis:
                        resultados_apis.append({
                            "api": r.get('api', 'unknown'),
                            "is_fake": r.get('is_fake', False),
                            "confidence": float(r.get('confidence', 0)),
                            "tempo_ms": r.get('tempo_ms', 0),
                        })

            except Exception as e:
                log.error(f"[{laudo.numero_laudo}] Erro na análise: {e}")
                veredicto = "REVISAR"
        else:
            log.warning(f"[{laudo.numero_laudo}] FakeDetectorCombo não disponível ou arquivo não existe")
            resultados_apis = [{"api": "local-mock", "is_fake": False, "confidence": 50.0}]

        # 3. Gerar PDF
        log.info(f"[{laudo.numero_laudo}] Gerando PDF...")

        generator = LaudoForenseGenerator()
        laudo_data = {
            "numero_laudo": laudo.numero_laudo,
            "cliente": {
                "nome": laudo.cliente.nome if laudo.cliente else "Desconhecido",
                "cnpj": laudo.cliente.cnpj if laudo.cliente else "00000000000000",
                "email": laudo.cliente.email if laudo.cliente else "nao@informado.com",
            },
            "arquivo_hash": laudo.arquivo_hash,
            "arquivo_nome": laudo.arquivo_nome,
            "arquivo_tamanho_mb": laudo.arquivo_tamanho_mb,
            "arquivo_tipo": laudo.arquivo_tipo,
            "veredicto": veredicto,
            "authenticity_score": authenticity_score,
            "consensus": consensus,
            "resultados_apis": resultados_apis,
            "descricao": laudo.descricao or "",
            "created_at": laudo.created_at.isoformat() if laudo.created_at else datetime.now().isoformat(),
        }

        pdf_bytes = generator.gerar_pdf(laudo_data)

        # Salvar PDF
        pdf_dir = Path("/data/forensic") if Path("/data").exists() else Path("/tmp/forensic")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f"{laudo.numero_laudo}.pdf"
        pdf_path.write_bytes(pdf_bytes)

        log.info(f"[{laudo.numero_laudo}] PDF salvo: {pdf_path}")

        # 4. Atualizar BD
        laudo.veredicto = veredicto
        laudo.authenticity_score = authenticity_score
        laudo.consensus = consensus
        laudo.pdf_path = str(pdf_path)
        laudo.resultados_apis = resultados_apis  # JSON
        laudo.status = 'processado'

        db.commit()
        log.info(f"[{laudo.numero_laudo}] ✅ Laudo finalizado: {veredicto}")

        return True

    except Exception as e:
        log.error(f"[laudo_id={laudo_id}] Erro fatal: {e}", exc_info=True)
        try:
            laudo = db.query(LaudoForense).filter(LaudoForense.id == laudo_id).first()
            if laudo:
                laudo.status = 'erro'
                db.commit()
        except:
            pass
        return False


# Entry point para scheduler/worker
def handle_forensic_job(job_dict: dict, db: Session) -> bool:
    """
    Handler chamado pelo scheduler de jobs.

    Args:
        job_dict: {"laudo_id": int, "arquivo_path": str, ...}
        db: Sessão do BD

    Returns:
        bool: Sucesso ou falha
    """
    laudo_id = job_dict.get('laudo_id')
    arquivo_path = job_dict.get('arquivo_path')

    if not laudo_id or not arquivo_path:
        log.error("Parâmetros obrigatórios faltando")
        return False

    return process_forensic_laudo(db, laudo_id, arquivo_path)
