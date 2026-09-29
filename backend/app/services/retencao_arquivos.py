import logging
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Laudo

logger = logging.getLogger(__name__)


def arquivar_documentos_antigos(db: Session) -> dict:
    """
    Cron mensal (1º dia, 02:00 UTC):
    - Busca docs com created_at > 5 anos
    - Move para storage frio (S3 Glacier / OneDrive Archive)
    - Marca status='arquivado', data_arquivamento=hoje
    - Mantém no BD (nunca deletar)
    """
    agora = datetime.utcnow()
    limite = agora - timedelta(days=5*365)
    resultados = {
        "laudos_arquivados": 0,
        "documentos_movidos": 0,
        "erros": 0,
        "data_execucao": agora.isoformat()
    }

    try:
        # Buscar laudos criados há mais de 5 anos que ainda não foram arquivados
        laudos_antigos = db.query(Laudo).filter(
            Laudo.created_at < limite,
            ~(Laudo.status == "arquivado")
        ).all()

        for laudo in laudos_antigos:
            try:
                # Verificar se tem arquivo associado
                arquivo_path = laudo.arquivo_pdf_path or laudo.arquivo_docx_path
                if arquivo_path and os.path.exists(arquivo_path):
                    # Aqui seria integração com S3/OneDrive
                    # Para agora, apenas marca como arquivado
                    # arquivo_id = mover_para_s3_glacier(arquivo_path)
                    pass

                # Marca como arquivado
                laudo.status = "arquivado"
                # Opcionalmente, pode adicionar campo data_arquivamento se necessário
                db.commit()

                resultados["laudos_arquivados"] += 1
                if arquivo_path:
                    resultados["documentos_movidos"] += 1

            except Exception as e:
                logger.error(f"Erro ao arquivar laudo {laudo.id}: {e}")
                resultados["erros"] += 1

        logger.info(f"Arquivamento de docs antigos concluído: {resultados}")
        return resultados

    except Exception as e:
        logger.error(f"Erro ao executar retenção de arquivos: {e}", exc_info=True)
        return {**resultados, "erros": 1}


# Funções auxiliares para integração S3/OneDrive (stubs)
def mover_para_s3_glacier(arquivo_path: str) -> str:
    """
    Move arquivo para S3 Glacier (armazenamento frio).
    Retorna ID do objeto armazenado.
    """
    # TODO: Implementar integração AWS S3
    pass


def mover_para_onedrive_archive(arquivo_path: str) -> str:
    """
    Move arquivo para pasta de arquivo no OneDrive.
    Retorna ID do objeto armazenado.
    """
    # TODO: Implementar integração OneDrive/Microsoft Graph
    pass
