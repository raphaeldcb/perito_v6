from .base import Base
from .user import User
from .role import Role
from .permission import Permission
from .tool import Tool
from .tool_permission import ToolPermission
from .audit_log import AuditLog
from .kanban import Kanban, KanbanColuna, KanbanCartao, KanbanHistorico, Intimacao, Oficio, OfficioTemplateVersion
from .processo import Processo
from .job import Job
from .parametro import Parametro
from .empresa import Empresa
from .coletador import Coletador, DocumentoColetador
from .financeiro import ExtratoBancario, LancamentoBancario
from .nota_fiscal import NotaFiscal
from .movimento import MovimentoProcesso
from .modelo import Modelo
from .indice_customizado import IndiceCustomizado
from .indice_cache import IndiceCache
from .padrao_calculo import PadraoCalculo
from .diario_config import DiarioConfig
from .oportunidade import Oportunidade
from .esaj_config import EsajConfig
from .protocolo import ItemProtocolo
from .laudo import Laudo, LaudoVersao, AuditoriaFable
from .engenharia import ModeloVistoria, Vistoria, VistoriaFoto, VistoriaAssinatura
from .fluxo_honorarios import HistoricoJuiz
from .despesa import Despesa
from .receita import Receita
from .dna import ParticipanteDNA, EnquadramentoDNA, TipoParentescoDNA, ResultadoDNA
from .workflow import WorkflowDefinition, WorkflowExecution
from .esaj_download import EsajDownload
from .produtividade import AssistProductionEvento, AssistProductionFinanceiroSummary
from .cerebro import AprendizadoEvento, PadrãoRAG, AuditoriaCAP
from .secure_vault import SecretVault, SecretRequest, SecretApproval, SecretAccessLog
from .inter import InterAccount, InterTransaction, InterPix, InterBoleto, InterCobranca, InterWebhook
from .inter_transacao import InterTransacao
from .projetocp import Comarca, Vara, Juiz
from .alerta import LaudoAlerta
from .delegacao import Delegacao
from .projetocp_financeiro import Financeiro, Pagamento, ParcelaFinanceira
from .proposta import PropostaMotor, PropostaStatus, PropostaFeedback, PropostaAnalisador
from .comunicacoes import EmailMessage, EmailConfig, EmailTemplate, EmailFeedback

# Aliases para compatibilidade com código legado
ComunicacaoMensagem = EmailMessage
ComunicacaoConfig = EmailConfig

__all__ = [
    "Job",
    "Parametro",
    "Empresa",
    "Coletador",
    "DocumentoColetador",
    "ExtratoBancario",
    "LancamentoBancario",
    "NotaFiscal",
    "MovimentoProcesso",
    "Modelo",
    "IndiceCustomizado",
    "IndiceCache",
    "PadraoCalculo",
    "DiarioConfig",
    "Oportunidade",
    "EsajConfig",
    "ItemProtocolo",
    "Base",
    "User",
    "Role",
    "Permission",
    "Tool",
    "ToolPermission",
    "AuditLog",
    "Kanban",
    "KanbanColuna",
    "KanbanCartao",
    "KanbanHistorico",
    "Processo",
    "Intimacao",
    "Oficio",
    "OfficioTemplateVersion",
    "Laudo",
    "LaudoVersao",
    "AuditoriaFable",
    "ModeloVistoria",
    "Vistoria",
    "VistoriaFoto",
    "VistoriaAssinatura",
    "HistoricoJuiz",
    "Despesa",
    "Receita",
    "ParticipanteDNA",
    "EnquadramentoDNA",
    "TipoParentescoDNA",
    "ResultadoDNA",
    "WorkflowDefinition",
    "WorkflowExecution",
    "EsajDownload",
    "AssistProductionEvento",
    "AssistProductionFinanceiroSummary",
    "AprendizadoEvento",
    "PadrãoRAG",
    "AuditoriaCAP",
    "SecretVault",
    "SecretRequest",
    "SecretApproval",
    "SecretAccessLog",
    "InterAccount",
    "InterTransaction",
    "InterPix",
    "InterBoleto",
    "InterCobranca",
    "InterWebhook",
    "InterTransacao",
    "Comarca",
    "Vara",
    "Juiz",
    "LaudoAlerta",
    "Delegacao",
    "Financeiro",
    "Pagamento",
    "ParcelaFinanceira",
    "PropostaMotor",
    "PropostaStatus",
    "PropostaFeedback",
    "PropostaAnalisador",
    "EmailMessage",
    "EmailConfig",
    "EmailTemplate",
    "EmailFeedback",
]
