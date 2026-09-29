"""
Rotas para gerenciamento de versões de templates de ofícios.

Endpoints:
- GET /api/v1/templates/tipos
- GET /api/v1/templates/{tipo}/versoes
- GET /api/v1/templates/{tipo}/ativa
- POST /api/v1/templates/upload
- PATCH /api/v1/templates/{versao_id}/deprecar
- GET /api/v1/templates/{tipo}/historico
- GET /api/v1/templates/stats
- GET /api/v1/templates/{versao_id}/download

SEGURANÇA (P0+P1):
- MIME Type Validation (P0): apenas application/vnd.openxmlformats-officedocument.wordprocessingml.document
- File Size Limit (P1): máx 10MB
- Data Isolation (P0): apenas admin pode criar/deprecar templates
"""
import logging
import io
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, OfficioTemplateVersion, Oficio
from app.services import get_db
from app.services.oficio_version_manager import (
    criar_versao_modelo,
    listar_versoes_por_tipo,
    obter_versao_ativa,
    obter_versao_por_id,
    deprecar_versao,
    obter_historico_versoes,
    contar_oficios_usando_versao,
    validar_versao_para_deprecacao,
    listar_tipos_disponíveis,
    obter_estatisticas_templates,
)
from app.services.oficio_placeholder_extractor import extrair_placeholders_docx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/templates", tags=["template-versions"])

# P0: MIME type válido para DOCX
ALLOWED_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# P1: Limite de tamanho de arquivo (10MB)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


# ===== Pydantic Models =====
class VersaoInfo(BaseModel):
    """Informações sobre uma versão de template."""
    id: str
    versao: str
    nome: str
    criada_por: str
    criada_em: str
    ativa: bool
    descricao: Optional[str] = None
    tags: List[str] = []
    num_placeholders: int = 0


class VersaoDetailadaResponse(BaseModel):
    """Resposta com detalhes de uma versão."""
    id: str
    versao: str
    nome: str
    tipo: str
    criada_por: str
    criada_em: str
    atualizada_por: Optional[str] = None
    atualizada_em: Optional[str] = None
    ativa: bool
    descricao: Optional[str] = None
    tags: List[str] = []
    placeholders: dict
    num_oficios_usando: int


class DeprecacaoRequest(BaseModel):
    """Request para deprecar uma versão."""
    confirmar: bool = Field(..., description="Confirmar deprecação")


class DeprecacaoResponse(BaseModel):
    """Response após deprecar uma versão."""
    versao: str
    status: str
    avisos: List[str]
    num_oficios_afetados: int


class UploadTemplateResponse(BaseModel):
    """Response após upload de novo template."""
    versao: str
    template_version_id: str
    tipo: str
    nome: str
    num_placeholders: int
    criado_em: str


class EstatisticasTemplatesResponse(BaseModel):
    """Estatísticas globais de templates."""
    total_versoes: int
    versoes_ativas: int
    versoes_inativas: int
    tipos_disponiveis: List[str]
    por_tipo: dict


# ===== Endpoints =====

@router.get("/tipos", response_model=List[str])
async def listar_tipos(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retorna lista de tipos de ofício disponíveis.

    Response:
    ["proposta", "defesa", "pagamento_final"]
    """
    try:
        tipos = listar_tipos_disponíveis(db)

        logger.info(f"Listagem de tipos: usuário {user.id}, {len(tipos)} tipos")

        return tipos

    except Exception as e:
        logger.error(f"Erro ao listar tipos: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao listar tipos de templates")


@router.get("/{tipo}/versoes", response_model=List[VersaoInfo])
async def listar_versoes(
    tipo: str,
    incluir_inativas: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retorna todas as versões de um tipo, mais recentes primeiro.

    Args:
        tipo: Tipo de ofício (proposta, defesa, pagamento_final)
        incluir_inativas: Se deve incluir versões deprecadas (default: false)

    Response:
    [
        {
            "versao": "v2.1",
            "nome": "Proposta Honorários v2.1",
            "criada_por": "Maria Silva",
            "criada_em": "2026-07-13T10:30:00",
            "ativa": true,
            "descricao": "Versão com melhorias na formatação",
            "tags": ["honorários", "2024"],
            "num_placeholders": 15
        }
    ]
    """
    try:
        versoes = listar_versoes_por_tipo(db, tipo, incluir_inativas=incluir_inativas)

        resultado = []
        for v in versoes:
            criador = v.created_by
            resultado.append(VersaoInfo(
                id=v.id,
                versao=v.versao_string,
                nome=v.nome,
                criada_por=criador.full_name if criador else 'Sistema',
                criada_em=v.created_at.isoformat() if v.created_at else '',
                ativa=v.is_ativa,
                descricao=v.descricao,
                tags=v.tags or [],
                num_placeholders=len(v.placeholders) if v.placeholders else 0,
            ))

        logger.info(
            f"Listagem de versões: tipo={tipo}, usuário={user.id}, "
            f"{len(resultado)} versões"
        )

        return resultado

    except Exception as e:
        logger.error(f"Erro ao listar versões: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao listar versões de templates")


@router.get("/{tipo}/ativa", response_model=VersaoInfo)
async def obter_versao_ativa_do_tipo(
    tipo: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retorna versão ativa mais recente de um tipo.

    Args:
        tipo: Tipo de ofício

    Response:
    {
        "id": "uuid-v2.1",
        "versao": "v2.1",
        "nome": "Proposta Honorários v2.1",
        ...
    }
    """
    try:
        versao = obter_versao_ativa(db, tipo)

        if not versao:
            raise HTTPException(
                404, f"Nenhuma versão ativa encontrada para o tipo '{tipo}'"
            )

        criador = versao.created_by
        resultado = VersaoInfo(
            id=versao.id,
            versao=versao.versao_string,
            nome=versao.nome,
            criada_por=criador.full_name if criador else 'Sistema',
            criada_em=versao.created_at.isoformat() if versao.created_at else '',
            ativa=versao.is_ativa,
            descricao=versao.descricao,
            tags=versao.tags or [],
            num_placeholders=len(versao.placeholders) if versao.placeholders else 0,
        )

        logger.info(f"Obtenção de versão ativa: tipo={tipo}, usuário={user.id}")

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter versão ativa: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao obter versão ativa de template")


@router.post("/upload", response_model=UploadTemplateResponse)
async def upload_template(
    arquivo: UploadFile = File(...),
    tipo: str = Form(...),
    nome: str = Form(...),
    descricao: Optional[str] = Form(None),
    tags_input: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload de novo template DOCX e criação de versão.

    P0 SEGURANÇA:
    - Apenas admin pode fazer upload
    - MIME type validation

    Form:
    - arquivo: DOCX file
    - tipo: proposta | defesa | pagamento_final
    - nome: Nome descritivo
    - descricao: Descrição (opcional)
    - tags_input: Tags separadas por vírgula (opcional)

    Response:
    {
        "versao": "v3.0",
        "template_version_id": "uuid-...",
        "tipo": "proposta",
        "nome": "Proposta Honorários v3.0",
        "num_placeholders": 15,
        "criado_em": "2026-07-13T..."
    }
    """
    try:
        # P0: Validar permissão
        if user.role != "admin":
            logger.warning(
                f"Acesso negado: usuário {user.id} tentou fazer upload de template"
            )
            raise HTTPException(403, "Apenas administradores podem fazer upload de templates")

        # Validar tipo
        if tipo not in ('proposta', 'defesa', 'pagamento_final'):
            raise HTTPException(400, f"Tipo inválido: {tipo}")

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
            raise HTTPException(
                413, f"Arquivo muito grande (máx {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB)"
            )

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
        placeholders_dict = extrair_placeholders_docx(arquivo_bytes)
        placeholders_map = {p: None for p in placeholders_dict}

        # Parse tags
        tags = []
        if tags_input:
            tags = [t.strip() for t in tags_input.split(',') if t.strip()]

        # Criar versão
        nova_versao = criar_versao_modelo(
            db=db,
            nome=nome,
            tipo=tipo,
            conteudo_docx=arquivo_bytes,
            placeholders=placeholders_map,
            created_by_id=user.id,
            descricao=descricao,
            tags=tags,
        )

        logger.info(
            f"Template upload processado: {nova_versao.id}, "
            f"versão={nova_versao.versao_string}, "
            f"{len(placeholders_dict)} placeholders, usuário={user.id}"
        )

        return UploadTemplateResponse(
            versao=nova_versao.versao_string,
            template_version_id=nova_versao.id,
            tipo=nova_versao.tipo,
            nome=nova_versao.nome,
            num_placeholders=len(placeholders_dict),
            criado_em=nova_versao.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Erro ao validar template: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Erro inesperado no upload de template: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao processar template")


@router.patch("/{versao_id}/deprecar", response_model=DeprecacaoResponse)
async def deprecar_template(
    versao_id: str,
    body: DeprecacaoRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Marca versão como inativa (deprecada).

    P0 SEGURANÇA:
    - Apenas admin pode deprecar

    Request:
    {
        "confirmar": true
    }

    Response:
    {
        "versao": "v2.0",
        "status": "deprecada",
        "avisos": [
            "15 ofício(s) estão usando esta versão e continuarão funcionando",
            "Esta é a última versão ativa do tipo..."
        ],
        "num_oficios_afetados": 15
    }
    """
    try:
        # P0: Validar permissão
        if user.role != "admin":
            logger.warning(
                f"Acesso negado: usuário {user.id} tentou deprecar template"
            )
            raise HTTPException(403, "Apenas administradores podem deprecar templates")

        if not body.confirmar:
            raise HTTPException(400, "Confirmação obrigatória para deprecação")

        # Validar se pode deprecar
        validacao = validar_versao_para_deprecacao(db, versao_id)
        if not validacao['pode_deprecar']:
            raise HTTPException(400, validacao['motivo'])

        # Deprecar
        versao_deprecada = deprecar_versao(db, versao_id, user.id)

        num_oficios = contar_oficios_usando_versao(db, versao_id)

        logger.info(
            f"Template deprecado: {versao_deprecada.versao_string} "
            f"(id={versao_id}, usuário={user.id}, oficios_afetados={num_oficios})"
        )

        return DeprecacaoResponse(
            versao=versao_deprecada.versao_string,
            status="deprecada",
            avisos=validacao['avisos'],
            num_oficios_afetados=num_oficios,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Erro ao deprecar template: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Erro ao deprecar template: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(500, "Erro ao deprecar template")


@router.get("/{tipo}/historico", response_model=List[VersaoInfo])
async def obter_historico_tipo(
    tipo: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retorna árvore de histórico de versões de um tipo (v1.0 → v2.0 → v2.1).

    Response: Lista ordenada cronologicamente (ascendente)
    """
    try:
        historico = obter_historico_versoes(db, tipo)

        resultado = [
            VersaoInfo(
                id=h['id'],
                versao=h['versao'],
                nome=h['nome'],
                criada_por=h['criada_por'],
                criada_em=h['criada_em'] or '',
                ativa=h['ativa'],
                descricao=h['descricao'],
                tags=h['tags'],
                num_placeholders=h['num_placeholders'],
            )
            for h in historico
        ]

        logger.info(f"Histórico obtido: tipo={tipo}, usuário={user.id}, {len(resultado)} versões")

        return resultado

    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao obter histórico de versões")


@router.get("/stats", response_model=EstatisticasTemplatesResponse)
async def obter_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retorna estatísticas globais de templates.

    Response:
    {
        "total_versoes": 5,
        "versoes_ativas": 3,
        "versoes_inativas": 2,
        "tipos_disponiveis": ["proposta", "defesa", "pagamento_final"],
        "por_tipo": {
            "proposta": {
                "total_versoes": 3,
                "versao_ativa": "v2.1",
                "oficios_usando": 42
            }
        }
    }
    """
    try:
        stats = obter_estatisticas_templates(db)

        logger.info(f"Estatísticas obtidas: usuário={user.id}")

        return EstatisticasTemplatesResponse(**stats)

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao obter estatísticas")


@router.get("/{versao_id}/download")
async def download_template(
    versao_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Download do DOCX de um template.

    P0: Validar permissão — apenas admin ou usuários que criaram podem baixar
    """
    try:
        versao = obter_versao_por_id(db, versao_id)
        if not versao:
            raise HTTPException(404, "Template não encontrado")

        # P0: Validar acesso
        if user.role != "admin" and versao.created_by_id != user.id:
            logger.warning(
                f"Acesso negado: usuário {user.id} tentou baixar template {versao_id}"
            )
            raise HTTPException(403, "Acesso negado a este template")

        if not versao.conteudo_docx:
            raise HTTPException(404, "Arquivo DOCX não encontrado")

        logger.info(f"Download de template: {versao_id}, usuário={user.id}")

        # Retorna arquivo em memória
        return FileResponse(
            io.BytesIO(versao.conteudo_docx),
            filename=f"template_{versao.tipo}_{versao.versao_string}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao baixar template: {e}")
        raise HTTPException(500, "Erro ao baixar arquivo")


@router.get("/{versao_id}", response_model=VersaoDetailadaResponse)
async def obter_versao_detalhada(
    versao_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retorna detalhes completos de uma versão.

    Response:
    {
        "id": "uuid",
        "versao": "v2.1",
        "nome": "Proposta Honorários v2.1",
        "tipo": "proposta",
        "criada_por": "Maria Silva",
        "criada_em": "2026-07-13T...",
        "atualizada_por": "João Santos",
        "atualizada_em": "2026-07-13T...",
        "ativa": true,
        "descricao": "...",
        "tags": ["honorários", "2024"],
        "placeholders": {"{{NUMERO_PROCESSO}}": "...", ...},
        "num_oficios_usando": 42
    }
    """
    try:
        versao = obter_versao_por_id(db, versao_id)
        if not versao:
            raise HTTPException(404, "Template não encontrado")

        criador = versao.created_by
        atualizador = versao.updated_by
        num_oficios = contar_oficios_usando_versao(db, versao_id)

        resultado = VersaoDetailadaResponse(
            id=versao.id,
            versao=versao.versao_string,
            nome=versao.nome,
            tipo=versao.tipo,
            criada_por=criador.full_name if criador else 'Sistema',
            criada_em=versao.created_at.isoformat() if versao.created_at else '',
            atualizada_por=atualizador.full_name if atualizador else None,
            atualizada_em=versao.updated_at.isoformat() if versao.updated_at else None,
            ativa=versao.is_ativa,
            descricao=versao.descricao,
            tags=versao.tags or [],
            placeholders=versao.placeholders or {},
            num_oficios_usando=num_oficios,
        )

        logger.info(f"Versão obtida: {versao_id}, usuário={user.id}")

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter versão: {e}", exc_info=True)
        raise HTTPException(500, "Erro ao obter detalhes do template")
