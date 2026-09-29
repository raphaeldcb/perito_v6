"""
Rotas para gerenciamento de ofícios — upload DOCX, mapeamento de campos e geração.

SEGURANÇA (P0+P1):
- MIME Type Validation (P0): apenas application/vnd.openxmlformats-officedocument.wordprocessingml.document
- File Size Limit (P1): máx 10MB
- Data Isolation (P0): valida acesso do usuário ao processo/ofício
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Processo, Oficio, KanbanCartao, KanbanColuna, Kanban, Intimacao
from app.services import get_db
from app.services.oficio_placeholder_extractor import (
    extrair_placeholders_docx,
    auto_mapear_campos,
    validar_mapeamento_manual,
)
from app.services.oficio_campo_mapeador import (
    salvar_upload_temporario,
    carregar_upload_temporario,
    deletar_upload_temporario,
    gerar_oficio_preenchido,
)
from app.decorators.require_feature import require_feature_flag

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/oficios", tags=["oficios"])

# P0: MIME type válido para DOCX
ALLOWED_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# P1: Limite de tamanho de arquivo (10MB)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


# ===== Pydantic Models =====
class MapeamentoManual(BaseModel):
    """Mapeamento manual de um campo."""
    tipo: str = Field(..., description="deslocamento, formula, numero, texto")
    valor: Optional[str] = None
    km: Optional[float] = None
    usar_gmaps: bool = False
    pedagio: Optional[float] = None
    taxa_km: Optional[float] = None
    formula: Optional[str] = None
    formato: Optional[str] = None


class MapeamentosRequest(BaseModel):
    """Request de mapeamento de campos."""
    temp_doc_id: str = Field(..., description="ID do upload temporário")
    processo_id: int = Field(..., description="ID do processo")
    mapeamentos_manual: dict[str, MapeamentoManual] = Field(
        default_factory=dict, description="Mapeamentos customizados"
    )
    salvar_como_modelo: bool = False
    observacoes: Optional[str] = None


class GerarOficioRequest(BaseModel):
    """Request para gerar ofício de um processo."""
    tipo: str = Field(default="proposta", description="proposta, ratifica, declina")
    template_version_id: Optional[str] = Field(default=None, description="UUID da versão do template, ou null para usar a ativa")
    revisor_id: Optional[int] = None
    observacoes: Optional[str] = None


# ===== Endpoints =====

@router.post("/upload-docx")
async def upload_docx(
    arquivo: UploadFile = File(...),
    processo_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload de DOCX e extração automática de placeholders.

    P0 SEGURANÇA:
    - MIME type validation: apenas application/vnd.openxmlformats-officedocument.wordprocessingml.document
    - File size limit (P1): máx 10MB

    Query: processo_id (obrigatório)
    Response:
    {
        "temp_doc_id": "xyz-temp-456",
        "placeholders_detectados": ["{{NUMERO_PROCESSO}}", "{{DESLOCAMENTO}}", ...],
        "mapeamentos_auto": {
            "{{NUMERO_PROCESSO}}": {"value": "0001234...", "source": "processo.numero_cnj"},
            "{{DESLOCAMENTO}}": null
        },
        "campos_sem_mapear": ["{{DESLOCAMENTO}}", "{{VALOR_DESLOCAMENTO}}"]
    }
    """
    try:
        # P0: Valida processo e acesso do usuário
        processo = db.query(Processo).get(processo_id)
        if not processo:
            raise HTTPException(404, "Processo não encontrado")

        # P0: Valida acesso (usuario é admin ou é responsável do processo)
        if user.role != "admin" and processo.responsavel_id != user.id:
            logger.warning(
                f"Acesso negado: usuário {user.id} tentou fazer upload "
                f"em processo {processo_id} (responsável: {processo.responsavel_id})"
            )
            raise HTTPException(403, "Acesso negado a este processo")

        # Lê arquivo
        arquivo_bytes = await arquivo.read()
        if not arquivo_bytes:
            raise HTTPException(400, "Arquivo vazio")

        # P1: Valida tamanho do arquivo
        file_size = len(arquivo_bytes)
        if file_size > MAX_UPLOAD_SIZE:
            logger.warning(
                f"Upload rejeitado: arquivo {arquivo.filename} "
                f"excede tamanho máximo ({file_size} > {MAX_UPLOAD_SIZE})"
            )
            raise HTTPException(413, f"Arquivo muito grande (máx {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB)")

        # Valida extensão
        if not arquivo.filename.lower().endswith(".docx"):
            raise HTTPException(400, "Apenas arquivos DOCX são aceitos")

        # P0: Valida MIME type
        content_type = arquivo.content_type or ""
        if content_type != ALLOWED_MIME_TYPE:
            logger.warning(
                f"Upload rejeitado: MIME type inválido. "
                f"Esperado '{ALLOWED_MIME_TYPE}', recebido '{content_type}'"
            )
            raise HTTPException(415, "Tipo de arquivo inválido. Use apenas DOCX.")

        # Extrai placeholders
        placeholders = extrair_placeholders_docx(arquivo_bytes)
        if not placeholders:
            logger.warning(f"DOCX não contém placeholders: {arquivo.filename}")

        # Mapeamento automático
        mapeamento_auto = auto_mapear_campos(processo, placeholders)

        # Salva temporariamente
        temp_doc_id = str(uuid.uuid4())
        salvar_upload_temporario(arquivo_bytes, temp_doc_id)

        logger.info(
            f"Upload DOCX processado (seguro): {temp_doc_id}, "
            f"{len(placeholders)} placeholders, "
            f"{len(mapeamento_auto['mapped'])} mapeados, "
            f"usuário {user.id}, processo {processo_id}"
        )

        return {
            "temp_doc_id": temp_doc_id,
            "placeholders_detectados": placeholders,
            "mapeamentos_auto": mapeamento_auto["mapped"],
            "campos_sem_mapear": mapeamento_auto["unmapped"],
            "arquivo_nome": arquivo.filename,
            "processo_id": processo_id,
            "enviado_em": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Erro ao processar DOCX: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Erro inesperado no upload DOCX: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao processar arquivo")


@router.post("/mapear-campos")
async def mapear_campos(
    body: MapeamentosRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Mapeamento manual de campos e geração de ofício preenchido.

    Request body:
    {
        "temp_doc_id": "xyz-temp-456",
        "mapeamentos_manual": {
            "{{DESLOCAMENTO}}": {
                "tipo": "deslocamento",
                "km": 45,
                "usar_gmaps": true,
                "pedagio": 12.50
            },
            "{{VALOR_DESLOCAMENTO}}": {
                "tipo": "formula",
                "formula": "km * 2.50 + IPCA_E"
            }
        },
        "salvar_como_modelo": false,
        "observacoes": "Revisar valor"
    }

    Response:
    {
        "oficio_id": 123,
        "status": "gerado",
        "documento_path": "/storage/oficios/...",
        "cartao_id": 456,
        "coluna_destino": "Aguardando Revisão",
        "timestamp": "2026-07-13T..."
    }
    """
    try:
        # Valida processo
        processo = db.query(Processo).get(body.processo_id)
        if not processo:
            raise HTTPException(404, "Processo não encontrado")

        # Carrega upload temporário
        try:
            docx_bytes = carregar_upload_temporario(body.temp_doc_id)
        except FileNotFoundError:
            raise HTTPException(
                400, f"Upload temporário expirou ou não encontrado: {body.temp_doc_id}"
            )

        # Extrai placeholders para saber quais são conhecidos
        placeholders = extrair_placeholders_docx(docx_bytes)

        # Mapeia automaticamente os campos conhecidos
        mapeamento_auto = auto_mapear_campos(processo, placeholders)

        # Valida todos os mapeamentos manuais
        mapeamentos_validados = {}
        for campo, mapeamento_data in body.mapeamentos_manual.items():
            if campo not in placeholders:
                logger.warning(f"Campo {campo} não está no documento")
                continue

            validado = validar_mapeamento_manual(
                campo, mapeamento_data.dict(exclude_none=True)
            )
            mapeamentos_validados[campo] = validado["valor_final"]

        # Monta mapeamento completo (automático + manual)
        mapeamentos_completos = {}
        mapeamentos_completos.update(
            {k: v["value"] for k, v in mapeamento_auto["mapped"].items()}
        )
        mapeamentos_completos.update(mapeamentos_validados)

        # Gera DOCX preenchido
        docx_path, hash_crc32 = gerar_oficio_preenchido(
            body.temp_doc_id, mapeamentos_completos, processo, user
        )

        # Busca ou cria primeira intimação
        intimacao = (
            db.query(Intimacao)
            .filter(Intimacao.processo_id == body.processo_id)
            .order_by(Intimacao.created_at.desc())
            .first()
        )
        if not intimacao:
            # Cria intimação genérica para o upload
            intimacao = Intimacao(
                processo_id=body.processo_id,
                origem="upload_adhoc",
                tipo="oficio_adhoc",
                assunto="Upload de ofício customizado",
                status="processada",
            )
            db.add(intimacao)
            db.flush()

        # Cria registro Oficio
        oficio = Oficio(
            intimacao_id=intimacao.id,
            processo_id=body.processo_id,
            revisor_id=body.processo_id if user else None,
            tipo="upload_adhoc",
            tipo_origem="upload_adhoc",
            template_upload_temp_id=body.temp_doc_id,
            arquivo_docx_path=docx_path,
            placeholders_mapeados=mapeamentos_completos,
            campos_manuais=list(mapeamentos_validados.keys()),
            status="gerado",
        )
        db.add(oficio)
        db.flush()

        # Auto-cria cartão kanban
        kanban = (
            db.query(Kanban)
            .filter(Kanban.perito_id == user.id)
            .first()
        )
        if not kanban:
            kanban = Kanban(perito_id=user.id, nome="Meu Kanban")
            db.add(kanban)
            db.flush()

        # Busca coluna "Aguardando Revisão"
        coluna = (
            db.query(KanbanColuna)
            .filter(KanbanColuna.kanban_id == kanban.id, KanbanColuna.nome == "Aguardando Revisão")
            .first()
        )
        if not coluna:
            coluna = KanbanColuna(
                kanban_id=kanban.id,
                nome="Aguardando Revisão",
                posicao=1,
                cor="#FFA500",
            )
            db.add(coluna)
            db.flush()

        # Cria cartão
        cartao = KanbanCartao(
            kanban_id=kanban.id,
            coluna_id=coluna.id,
            processo_id=body.processo_id,
            titulo=f"Ofício ADHOC - {processo.numero_cnj}",
            descricao=body.observacoes or "",
            laudo_docx_path=docx_path,
            status_revisao="em_rascunho",
        )
        db.add(cartao)
        db.flush()

        # Atualiza ofício com cartão
        oficio.cartao_id = cartao.id
        oficio.status = "aguardando_revisao"

        db.commit()

        # Deleta upload temporário
        deletar_upload_temporario(body.temp_doc_id)

        logger.info(f"Ofício adhoc gerado: {oficio.id}, cartão: {cartao.id}")

        return {
            "oficio_id": oficio.id,
            "status": oficio.status,
            "documento_path": docx_path,
            "cartao_id": cartao.id,
            "coluna_destino": "Aguardando Revisão",
            "tipo_oficio": "upload_adhoc",
            "mapeamentos_aplicados": len(mapeamentos_completos),
            "hash_integridade": hash_crc32,
            "criado_em": oficio.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no mapeamento de campos: {e}", exc_info=True)
        raise HTTPException(500, f"Erro ao processar mapeamento: {str(e)}")


@router.post("/processos/{processo_id}/gerar-oficio")
async def gerar_oficio_processo(
    processo_id: int,
    body: GerarOficioRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Gera ofício de um processo via modelo padrão com suporte a versionamento.

    Args:
        processo_id: ID do processo
        body: GerarOficioRequest
            - tipo: Tipo de ofício (proposta, ratifica, declina)
            - template_version_id: UUID da versão (ou null para usar ativa)
            - revisor_id: ID do revisor (opcional)
            - observacoes: Observações (opcional)

    Response:
    {
        "oficio_id": 123,
        "status": "gerado",
        "documento_path": "/storage/oficios/...",
        "cartao_id": 456,
        "coluna_destino": "Aguardando Revisão",
        "template_version": "v2.1",
        "criado_em": "2026-07-13T..."
    }
    """
    try:
        from app.models import OfficioTemplateVersion
        from app.services.oficio_version_manager import obter_versao_ativa, obter_versao_por_id
        from app.services.oficio_generator import gerar_oficio as gerar_oficio_padrao

        # Valida processo
        processo = db.query(Processo).get(processo_id)
        if not processo:
            raise HTTPException(404, "Processo não encontrado")

        # Busca primeira intimação (para compatibilidade com gerador existente)
        intimacao = (
            db.query(Intimacao)
            .filter(Intimacao.processo_id == processo_id)
            .order_by(Intimacao.created_at.desc())
            .first()
        )

        if not intimacao:
            raise HTTPException(
                400, f"Processo {processo_id} sem intimações. Crie uma antes de gerar ofício."
            )

        # Seleciona versão do template
        if body.template_version_id:
            template_version = obter_versao_por_id(db, body.template_version_id)
            if not template_version:
                raise HTTPException(404, f"Template versão {body.template_version_id} não encontrado")
        else:
            # Usa versão ativa do tipo
            template_version = obter_versao_ativa(db, body.tipo)
            if not template_version:
                # Fallback: usa gerador padrão se não houver versão
                logger.warning(f"Nenhuma versão ativa para tipo {body.tipo}, usando gerador padrão")
                template_version = None

        # Gera DOCX
        resultado = gerar_oficio_padrao(intimacao, tipo=body.tipo)
        docx_path = resultado["oficio_docx_path"]

        # Cria registro Oficio
        oficio = Oficio(
            intimacao_id=intimacao.id,
            processo_id=processo_id,
            revisor_id=body.revisor_id,
            tipo=body.tipo,
            tipo_origem="modelo",
            template_version_id=template_version.id if template_version else None,
            arquivo_docx_path=docx_path,
            status="gerado",
        )
        db.add(oficio)
        db.flush()  # obtém ID

        # Auto-cria cartão kanban se não existir
        kanban = (
            db.query(Kanban)
            .filter(Kanban.perito_id == user.id)
            .first()
        )
        if not kanban:
            kanban = Kanban(perito_id=user.id, nome="Meu Kanban")
            db.add(kanban)
            db.flush()

        # Busca coluna "Aguardando Revisão"
        coluna = (
            db.query(KanbanColuna)
            .filter(KanbanColuna.kanban_id == kanban.id, KanbanColuna.nome == "Aguardando Revisão")
            .first()
        )
        if not coluna:
            # Cria coluna se não existir
            coluna = KanbanColuna(
                kanban_id=kanban.id,
                nome="Aguardando Revisão",
                posicao=1,
                cor="#FFA500",  # laranja
            )
            db.add(coluna)
            db.flush()

        # Cria cartão
        cartao = KanbanCartao(
            kanban_id=kanban.id,
            coluna_id=coluna.id,
            processo_id=processo_id,
            titulo=f"Ofício {body.tipo.upper()} - {processo.numero_cnj}",
            descricao=body.observacoes or "",
            laudo_docx_path=docx_path,
            status_revisao="em_rascunho",
        )
        db.add(cartao)
        db.flush()

        # Atualiza ofício com referência ao cartão
        oficio.cartao_id = cartao.id
        oficio.status = "aguardando_revisao"

        db.commit()

        logger.info(
            f"Ofício gerado: {oficio.id}, cartão: {cartao.id}, processo: {processo_id}, "
            f"template_version: {template_version.versao_string if template_version else 'padrão'}"
        )

        return {
            "oficio_id": oficio.id,
            "status": oficio.status,
            "documento_path": docx_path,
            "cartao_id": cartao.id,
            "coluna_destino": "Aguardando Revisão",
            "tipo_oficio": body.tipo,
            "template_version": template_version.versao_string if template_version else None,
            "criado_em": oficio.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar ofício: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao gerar ofício: {str(e)}")


@router.get("/oficio/{oficio_id}/download")
async def download_oficio(
    oficio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Download do DOCX de um ofício.

    P0: Valida acesso — usuario só pode baixar ofícios de seus processos.
    """
    try:
        oficio = db.query(Oficio).get(oficio_id)
        if not oficio:
            raise HTTPException(404, "Ofício não encontrado")

        # P0: Valida acesso ao processo
        processo = oficio.processo
        if not processo:
            raise HTTPException(500, "Processo associado ao ofício não encontrado")

        if user.role != "admin" and processo.responsavel_id != user.id:
            logger.warning(
                f"Acesso negado: usuário {user.id} tentou baixar ofício {oficio_id} "
                f"do processo {processo.id} (responsável: {processo.responsavel_id})"
            )
            raise HTTPException(403, "Acesso negado a este ofício")

        docx_path = oficio.arquivo_docx_path
        if not docx_path or not __import__("os").path.exists(docx_path):
            raise HTTPException(404, "Arquivo DOCX não encontrado")

        logger.info(f"Download de ofício: {oficio_id}, usuário {user.id}")

        return FileResponse(
            docx_path,
            filename=f"oficio_{oficio.tipo}_{oficio_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao baixar ofício: {e}")
        raise HTTPException(500, "Erro ao baixar arquivo")


@router.get("/pendentes-revisao")
async def pendentes_revisao(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Lista ofícios pendentes de revisão.

    P0: Filtra por usuário — admin vê todos, outros usuários veem apenas seus processos.
    """
    try:
        query = db.query(Oficio).filter(Oficio.status == "aguardando_revisao")

        # P0: Data Isolation — não-admin só veem seus processos
        if user.role != "admin":
            query = query.join(Processo).filter(
                Processo.responsavel_id == user.id
            )

        oficios = query.order_by(Oficio.created_at.desc()).limit(100).all()

        resultado = []
        for o in oficios:
            p = o.processo
            resultado.append({
                "oficio_id": o.id,
                "tipo": o.tipo,
                "status": o.status,
                "processo_id": o.processo_id,
                "numero_cnj": p.numero_cnj if p else None,
                "juiz": p.juiz if p else None,
                "vara": p.vara if p else None,
                "cartao_id": o.cartao_id,
                "criado_em": o.created_at.isoformat() if o.created_at else None,
                "observacoes": o.erros,
            })

        logger.info(
            f"Listagem de ofícios pendentes: usuário {user.id}, "
            f"{len(oficios)} ofícios (filtrado por role={user.role})"
        )

        return resultado

    except Exception as e:
        logger.error(f"Erro ao listar pendentes: {e}")
        raise HTTPException(500, "Erro ao listar ofícios pendentes")


@router.post("/oficio/{oficio_id}/revisor-assinou")
async def registrar_revisao(
    oficio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Registra que revisor assinou (aprovou) um ofício."""
    try:
        oficio = db.query(Oficio).get(oficio_id)
        if not oficio:
            raise HTTPException(404, "Ofício não encontrado")

        oficio.revisor_id = user.id
        oficio.revisor_timestamp = datetime.utcnow()
        oficio.status = "revisor_assinou"

        # Move cartão para próxima coluna
        if oficio.cartao_id:
            cartao = db.query(KanbanCartao).get(oficio.cartao_id)
            if cartao:
                # Busca próxima coluna (normalmente "Protocolo")
                proxima_coluna = (
                    db.query(KanbanColuna)
                    .filter(
                        KanbanColuna.kanban_id == cartao.kanban_id,
                        KanbanColuna.posicao > cartao.coluna.posicao,
                    )
                    .order_by(KanbanColuna.posicao)
                    .first()
                )
                if proxima_coluna:
                    cartao.coluna_id = proxima_coluna.id

        db.commit()

        logger.info(f"Ofício {oficio_id} aprovado por revisor {user.id}")

        return {
            "oficio_id": oficio.id,
            "status": oficio.status,
            "revisor_id": user.id,
            "timestamp": oficio.revisor_timestamp.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao registrar revisão: {e}")
        db.rollback()
        raise HTTPException(500, "Erro ao registrar revisão")
