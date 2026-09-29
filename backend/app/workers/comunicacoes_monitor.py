"""Wrapper para o worker de monitoramento de comunicações judiciais."""

from app.workers import monitor_comunicacoes


class ComunicacoesMonitorWorker:
    """Adaptador para o worker de comunicações."""

    def __init__(self, db=None):
        """Inicializa worker (db é opcional, worker usa SessionLocal)."""
        self.db = db

    def executar(self, conta_email: str = "financeiro@ipcms.com.br", limite: int = 50) -> dict:
        """Executa monitoramento e retorna estatísticas."""
        return monitor_comunicacoes.processar_caixa_entrada(conta_email, limite)
