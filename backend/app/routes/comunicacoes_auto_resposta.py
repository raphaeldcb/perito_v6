"""Rotas para auto-resposta de comunicações judiciais."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas.comunicacoes_templates import (
    ComunicacaoTemplateSchema,
    ComunicacaoTemplateCreateSchema,
    AutoRespostaPreviewSchema,
    SugerirTemplatesResponse,
)
from app.services.comunicacoes_auto_resposta import AutoRespostaService
from app.models import ComunicacaoMensagem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/comunicacoes/auto-resposta", tags=["auto-resposta"])


def get_db():
    """Dependency: database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/templates", response_model=list[ComunicacaoTemplateSchema])
def listar_templates(
    ativo: bool = Query(True),
    tipo: str = Query(None),
    db: Session = Depends(get_db),
):
    """Lista templates de resposta automática."""
    service = AutoRespostaService(db)
    templates = service.listar_templates(ativo=ativo, tipo=tipo)
    return [
        ComunicacaoTemplateSchema.model_validate(
            {
                "id": t.id,
                "nome": t.nome,
                "tipo": t.tipo,
                "assunto_template": t.assunto_template,
                "corpo_html": t.corpo_html,
                "corpo_texto": t.corpo_texto,
                "descricao": t.descricao,
                "aplicar_automaticamente": t.aplicar_automaticamente,
                "triggar_palavras_chave": t.triggar_palavras_chave,
                "triggar_tipo_processo": t.triggar_tipo_processo,
                "triggar_min_confianca": t.triggar_min_confianca,
                "ativo": t.ativo,
                "criado_em": t.criado_em,
                "atualizado_em": t.atualizado_em,
                "atualizado_por": t.atualizado_por,
            }
        )
        for t in templates
    ]


@router.post("/templates", response_model=ComunicacaoTemplateSchema)
def criar_template(
    data: ComunicacaoTemplateCreateSchema,
    atualizado_por: str = Query("admin@ipcms.com.br"),
    db: Session = Depends(get_db),
):
    """Cria novo template de resposta automática."""
    try:
        service = AutoRespostaService(db)
        template = service.criar_template(
            nome=data.nome,
            tipo=data.tipo,
            assunto_template=data.assunto_template,
            corpo_html=data.corpo_html,
            corpo_texto=data.corpo_texto,
            descricao=data.descricao,
            aplicar_automaticamente=data.aplicar_automaticamente,
            triggar_palavras_chave=data.triggar_palavras_chave,
            triggar_tipo_processo=data.triggar_tipo_processo,
            triggar_min_confianca=data.triggar_min_confianca,
            atualizado_por=atualizado_por,
        )

        return ComunicacaoTemplateSchema.model_validate(
            {
                "id": template.id,
                "nome": template.nome,
                "tipo": template.tipo,
                "assunto_template": template.assunto_template,
                "corpo_html": template.corpo_html,
                "corpo_texto": template.corpo_texto,
                "descricao": template.descricao,
                "aplicar_automaticamente": template.aplicar_automaticamente,
                "triggar_palavras_chave": template.triggar_palavras_chave,
                "triggar_tipo_processo": template.triggar_tipo_processo,
                "triggar_min_confianca": template.triggar_min_confianca,
                "ativo": template.ativo,
                "criado_em": template.criado_em,
                "atualizado_em": template.atualizado_em,
                "atualizado_por": template.atualizado_por,
            }
        )

    except Exception as e:
        logger.error(f"Erro criando template: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar template")


@router.get("/sugerir")
def sugerir_templates(
    mensagem_id: int = Query(...),
    db: Session = Depends(get_db),
) -> SugerirTemplatesResponse:
    """Sugere templates aplicáveis para uma mensagem."""
    try:
        mensagem = db.query(ComunicacaoMensagem).filter_by(id=mensagem_id).first()
        if not mensagem:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada")

        service = AutoRespostaService(db)
        templates_sugeridos = service.sugerir_templates(mensagem)

        return SugerirTemplatesResponse(
            mensagem_id=mensagem_id,
            templates_sugeridos=[
                ComunicacaoTemplateSchema.model_validate(
                    {
                        "id": t.id,
                        "nome": t.nome,
                        "tipo": t.tipo,
                        "assunto_template": t.assunto_template,
                        "corpo_html": t.corpo_html,
                        "corpo_texto": t.corpo_texto,
                        "descricao": t.descricao,
                        "aplicar_automaticamente": t.aplicar_automaticamente,
                        "triggar_palavras_chave": t.triggar_palavras_chave,
                        "triggar_tipo_processo": t.triggar_tipo_processo,
                        "triggar_min_confianca": t.triggar_min_confianca,
                        "ativo": t.ativo,
                        "criado_em": t.criado_em,
                        "atualizado_em": t.atualizado_em,
                        "atualizado_por": t.atualizado_por,
                    }
                )
                for t in templates_sugeridos
            ],
            total=len(templates_sugeridos),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro sugerindo templates: {e}")
        raise HTTPException(status_code=500, detail="Erro ao sugerir templates")


@router.post("/preparar")
def preparar_resposta(
    mensagem_id: int = Query(...),
    template_id: int = Query(...),
    db: Session = Depends(get_db),
) -> AutoRespostaPreviewSchema:
    """Prepara resposta para aprovação manual (não envia)."""
    try:
        service = AutoRespostaService(db)
        resposta = service.preparar_resposta(mensagem_id, template_id)

        if not resposta:
            raise HTTPException(status_code=400, detail="Falha ao preparar resposta")

        return AutoRespostaPreviewSchema(
            assunto=resposta.assunto_enviado,
            corpo_html=resposta.corpo_html_enviado,
            destinatario=resposta.destinatario,
        )

    except Exception as e:
        logger.error(f"Erro preparando resposta: {e}")
        raise HTTPException(status_code=500, detail="Erro ao preparar resposta")


@router.post("/enviar")
def enviar_resposta(
    resposta_id: int = Query(...),
    aprovado_por: str = Query("admin@ipcms.com.br"),
    db: Session = Depends(get_db),
) -> dict:
    """Envia resposta preparada."""
    try:
        service = AutoRespostaService(db)
        sucesso = service.enviar_resposta(resposta_id, aprovado_por=aprovado_por)

        if sucesso:
            return {"status": "enviada", "resposta_id": resposta_id}
        else:
            return {"status": "erro", "resposta_id": resposta_id, "mensagem": "Falha ao enviar"}

    except Exception as e:
        logger.error(f"Erro enviando resposta: {e}")
        raise HTTPException(status_code=500, detail="Erro ao enviar resposta")
