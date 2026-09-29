"""
ProjetoCP Phase 2: Services for Laudo operations
Integração com Qwen, RAG, e versionamento
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.laudo import Laudo, LaudoVersao
from app.models.projetocp_laudos import (
    LaudoQuesito, LaudoAnexo, LaudoHonorario, LaudoRevenda
)
from app.models.job import Job
from app.schemas.projetocp_laudos import (
    LaudoQuesitoCriarRequest, LaudoQuesitoAtualizar,
    LaudoHonorarioCriarRequest, LaudoGeracaoAutomaticaRequest
)

logger = logging.getLogger(__name__)


class LaudoQuesitoService:
    """Serviço de gerenciamento de quesitos"""

    @staticmethod
    def criar_quesitos_lote(db: Session, laudo_id: int, quesitos: List[Dict[str, Any]]) -> List[LaudoQuesito]:
        """Criar múltiplos quesitos (usado na extração automática do Qwen)"""
        try:
            quesitos_criados = []
            for q in quesitos:
                quesito = LaudoQuesito(
                    laudo_id=laudo_id,
                    numero=q.get("numero"),
                    pergunta=q.get("pergunta"),
                    tipo=q.get("tipo", "ordinario"),
                    relevancia=q.get("relevancia", 5),
                    status="nao_respondido"
                )
                db.add(quesito)
                quesitos_criados.append(quesito)

            db.commit()
            logger.info(f"Criados {len(quesitos_criados)} quesitos para laudo {laudo_id}")
            return quesitos_criados
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao criar quesitos: {str(e)}")
            raise

    @staticmethod
    def atualizar_quesito(db: Session, quesito_id: int, dados: LaudoQuesitoAtualizar) -> LaudoQuesito:
        """Atualizar quesito (típico após resposta do Qwen ou edição manual)"""
        quesito = db.query(LaudoQuesito).filter(LaudoQuesito.id == quesito_id).first()
        if not quesito:
            raise ValueError(f"Quesito {quesito_id} não encontrado")

        for field, value in dados.dict(exclude_unset=True).items():
            if value is not None:
                setattr(quesito, field, value)

        quesito.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Quesito {quesito_id} atualizado")
        return quesito

    @staticmethod
    def marcar_respondido(db: Session, quesito_id: int, resposta: str, fontes_rag: Optional[List[Dict]] = None):
        """Marcar quesito como respondido com resposta e fontes RAG opcionais"""
        quesito = db.query(LaudoQuesito).filter(LaudoQuesito.id == quesito_id).first()
        if not quesito:
            raise ValueError(f"Quesito {quesito_id} não encontrado")

        quesito.resposta = resposta
        quesito.status = "respondido"
        if fontes_rag:
            quesito.fontes_rag = fontes_rag

        db.commit()
        return quesito

    @staticmethod
    def listar_quesitos_por_laudo(db: Session, laudo_id: int) -> List[LaudoQuesito]:
        """Listar todos os quesitos de um laudo ordenados por número"""
        return db.query(LaudoQuesito).filter(
            LaudoQuesito.laudo_id == laudo_id
        ).order_by(LaudoQuesito.numero).all()

    @staticmethod
    def contar_quesitos_respondidos(db: Session, laudo_id: int) -> int:
        """Contar quantos quesitos já foram respondidos"""
        return db.query(LaudoQuesito).filter(
            and_(LaudoQuesito.laudo_id == laudo_id, LaudoQuesito.status == "respondido")
        ).count()


class LaudoAnexoService:
    """Serviço de gerenciamento de anexos"""

    @staticmethod
    def criar_anexo(db: Session, laudo_id: int, tipo: str, titulo: str,
                   arquivo_path: str, descricao: Optional[str] = None,
                   pagina_ref: Optional[int] = None, upload_por_id: Optional[int] = None) -> LaudoAnexo:
        """Criar novo anexo do laudo"""
        anexo = LaudoAnexo(
            laudo_id=laudo_id,
            tipo=tipo,
            titulo=titulo,
            descricao=descricao,
            arquivo_path=arquivo_path,
            pagina_referencia=pagina_ref,
            upload_por_id=upload_por_id
        )
        db.add(anexo)
        db.commit()
        logger.info(f"Anexo '{titulo}' criado para laudo {laudo_id}")
        return anexo

    @staticmethod
    def listar_anexos_por_laudo(db: Session, laudo_id: int) -> List[LaudoAnexo]:
        """Listar todos os anexos de um laudo"""
        return db.query(LaudoAnexo).filter(LaudoAnexo.laudo_id == laudo_id).all()

    @staticmethod
    def deletar_anexo(db: Session, anexo_id: int):
        """Deletar um anexo"""
        anexo = db.query(LaudoAnexo).filter(LaudoAnexo.id == anexo_id).first()
        if not anexo:
            raise ValueError(f"Anexo {anexo_id} não encontrado")

        db.delete(anexo)
        db.commit()
        logger.info(f"Anexo {anexo_id} deletado")


class LaudoHonorarioService:
    """Serviço de cálculo e gerenciamento de honorários"""

    # Tabela OAB de referência (podem ser atualizadas via parametro)
    TABELA_HONORARIOS_BASE = {
        "grafotecnica": Decimal("2500.00"),
        "engenharia_civil": Decimal("3500.00"),
        "engenharia_mecanica": Decimal("3000.00"),
        "engenharia_eletrica": Decimal("3000.00"),
        "agronomia": Decimal("2800.00"),
        "medicina": Decimal("3500.00"),
        "odontologia": Decimal("2500.00"),
        "psicologia": Decimal("2500.00"),
        "contabilidade": Decimal("3000.00"),
        "economia": Decimal("3000.00"),
        "topografia": Decimal("2200.00"),
    }

    @staticmethod
    def calcular_valor_final(valor_base: Decimal, adicional_complexidade: Decimal,
                            adicional_deslocamento: Decimal, deducao_desconto: Decimal) -> Decimal:
        """Calcular valor final = (base + adic) - deducao"""
        return (valor_base + adicional_complexidade + adicional_deslocamento) - deducao_desconto

    @staticmethod
    def criar_honorario(db: Session, dados: LaudoHonorarioCriarRequest, calculado_por_id: Optional[int] = None) -> LaudoHonorario:
        """Criar registro de honorário com cálculo"""
        # Calcular valor_final
        valor_final = LaudoHonorarioService.calcular_valor_final(
            dados.valor_base,
            dados.adicional_complexidade,
            dados.adicional_deslocamento,
            dados.deducao_desconto
        )

        honorario = LaudoHonorario(
            laudo_id=dados.laudo_id,
            processo_id=dados.processo_id,
            area=dados.area.value if hasattr(dados.area, 'value') else dados.area,
            tipo_calculo=dados.tipo_calculo,
            valor_base=dados.valor_base,
            adicional_complexidade=dados.adicional_complexidade,
            adicional_deslocamento=dados.adicional_deslocamento,
            deducao_desconto=dados.deducao_desconto,
            valor_final=valor_final,
            percentual_sucumbencia=dados.percentual_sucumbencia,
            calculado_por_id=calculado_por_id
        )

        db.add(honorario)
        db.commit()
        logger.info(f"Honorário criado para laudo {dados.laudo_id}: R$ {valor_final}")
        return honorario

    @staticmethod
    def obter_valor_tabela(area: str) -> Decimal:
        """Obter valor de tabela OAB para uma área"""
        return LaudoHonorarioService.TABELA_HONORARIOS_BASE.get(
            area, Decimal("2500.00")
        )

    @staticmethod
    def calcular_sucumbencia(valor_laudo: Decimal, percentual: Decimal = Decimal("90")) -> Decimal:
        """Calcular valor estimado de sucumbência (típico 90% do valor do laudo)"""
        return (valor_laudo * percentual) / Decimal("100")

    @staticmethod
    def obter_honorario_por_laudo(db: Session, laudo_id: int) -> Optional[LaudoHonorario]:
        """Obter registro de honorário de um laudo"""
        return db.query(LaudoHonorario).filter(LaudoHonorario.laudo_id == laudo_id).first()


class LaudoGeracaoService:
    """Serviço de geração automática de laudos (integração Qwen + RAG)"""

    @staticmethod
    def criar_job_geracao(db: Session, laudo_id: int, processo_id: int, area: str,
                         etapa: str = "extracao_quesitos", usar_rag: bool = True,
                         modelo_ia: str = "qwen-3.6") -> Job:
        """Criar job para processamento de laudo em background"""
        payload = {
            "laudo_id": laudo_id,
            "processo_id": processo_id,
            "area": area,
            "etapa": etapa,
            "usar_rag": usar_rag,
            "modelo_ia": modelo_ia
        }

        job = Job(
            tipo=f"laudo_geracao_{etapa}",
            payload=payload,
            status="pendente",
            tentativas=0
        )

        db.add(job)
        db.commit()
        logger.info(f"Job de geração de laudo criado: {job.id} (etapa: {etapa})")
        return job

    @staticmethod
    def atualizar_etapa_laudo(db: Session, laudo_id: int, nova_etapa: str):
        """Atualizar etapa de um laudo"""
        laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
        if not laudo:
            raise ValueError(f"Laudo {laudo_id} não encontrado")

        laudo.status = nova_etapa
        laudo.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Laudo {laudo_id} movido para etapa: {nova_etapa}")

    @staticmethod
    def registrar_revenda_log(db: Session, laudo_id: int, etapa: str,
                             modelo_ia: str = "qwen-3.6", resultado_raw: Optional[Dict] = None,
                             tempo_segundos: Optional[int] = None, erro: Optional[str] = None,
                             processado_por: str = "mac_agent", acertou_100_porcento: bool = False):
        """Registrar log de processamento do laudo para auditoria"""
        revenda = LaudoRevenda(
            laudo_id=laudo_id,
            etapa=etapa,
            modelo_ia=modelo_ia,
            tempo_processamento_segundos=tempo_segundos,
            resultado_raw=resultado_raw,
            status="sucesso" if not erro else "erro",
            erro=erro,
            processado_por=processado_por
        )

        db.add(revenda)
        db.flush()

        # RETROALIMENTAÇÃO: se aprovado sem alterações = registrar sucesso 100%
        if acertou_100_porcento:
            if not resultado_raw:
                resultado_raw = {}
            resultado_raw["feedback_resultado"] = "ACERTOU_100_PORCENTO"
            revenda.resultado_raw = resultado_raw

            # Incrementar contador de sucessos para esta especialidade
            laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
            if laudo and hasattr(laudo, 'especialidade'):
                from app.models.projetocp_laudos import LaudoEspecialidadeStats
                stats = db.query(LaudoEspecialidadeStats).filter(
                    LaudoEspecialidadeStats.especialidade == laudo.especialidade
                ).first()
                if not stats:
                    stats = LaudoEspecialidadeStats(especialidade=laudo.especialidade)
                    db.add(stats)
                    db.flush()
                stats.total_gerados += 1
                stats.total_acertos_100 += 1
                stats.confianca_proxima_geracao = min(95, stats.total_acertos_100 * 5)  # Sobe confiança
                logger.info(f"🎯 SUCESSO 100%: Laudo {laudo_id} ({laudo.especialidade}) — próximas: confiança={stats.confianca_proxima_geracao}%")

        db.commit()
        logger.info(f"Log de revenda registrado para laudo {laudo_id}: {etapa}")
        return revenda


class LaudoValidacaoService:
    """Serviço de validação de consistência e completude de laudos"""

    @staticmethod
    def validar_estrutura_completa(db: Session, laudo_id: int) -> Dict[str, Any]:
        """Validar se laudo tem estrutura mínima completa"""
        laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
        if not laudo:
            raise ValueError(f"Laudo {laudo_id} não encontrado")

        quesitos = LaudoQuesitoService.listar_quesitos_por_laudo(db, laudo_id)
        quesitos_respondidos = LaudoQuesitoService.contar_quesitos_respondidos(db, laudo_id)
        honorario = LaudoHonorarioService.obter_honorario_por_laudo(db, laudo_id)
        anexos = LaudoAnexoService.listar_anexos_por_laudo(db, laudo_id)

        validacoes = {
            "laudo_id": laudo_id,
            "tem_quesitos": len(quesitos) > 0,
            "quesitos_respondidos": quesitos_respondidos == len(quesitos),
            "tem_honorario": honorario is not None,
            "tem_anexos": len(anexos) > 0,
            "tem_arquivo_pdf": laudo.arquivo_pdf_path is not None,
            "status": laudo.status,
            "total_quesitos": len(quesitos),
            "quesitos_resp": quesitos_respondidos,
            "num_anexos": len(anexos),
        }

        # Verificar se está pronto para protocolo
        pronto_protocolo = (
            validacoes["tem_quesitos"] and
            validacoes["quesitos_respondidos"] and
            validacoes["tem_honorario"] and
            validacoes["tem_arquivo_pdf"]
        )

        validacoes["pronto_protocolo"] = pronto_protocolo
        return validacoes

    @staticmethod
    def diagnosticar_laudo(db: Session, laudo_id: int) -> Dict[str, Any]:
        """Gerar diagnóstico completo de um laudo com recomendações"""
        validacao = LaudoValidacaoService.validar_estrutura_completa(db, laudo_id)

        recomendacoes = []
        if not validacao["tem_quesitos"]:
            recomendacoes.append("Extrair quesitos da intimação")
        if not validacao["quesitos_respondidos"]:
            recomendacoes.append(f"Responder {validacao['total_quesitos'] - validacao['quesitos_resp']} quesito(s) pendente(s)")
        if not validacao["tem_honorario"]:
            recomendacoes.append("Calcular honorários")
        if not validacao["tem_arquivo_pdf"]:
            recomendacoes.append("Gerar/anexar PDF do laudo")

        return {
            "validacao": validacao,
            "recomendacoes": recomendacoes,
            "proxima_acao": recomendacoes[0] if recomendacoes else "Laudo pronto para protocolo"
        }
