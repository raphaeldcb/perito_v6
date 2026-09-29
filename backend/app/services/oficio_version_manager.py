"""
Gerenciador de versões de templates de ofícios.

Responsabilidades:
- Criar novas versões de modelos
- Listar versões por tipo
- Obter versão ativa
- Deprecar versões (mantém histórico)
- Extrair histórico de versões
"""
import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import OfficioTemplateVersion, User

logger = logging.getLogger(__name__)


def criar_versao_modelo(
    db: Session,
    nome: str,
    tipo: str,
    conteudo_docx: bytes,
    placeholders: Dict[str, str],
    created_by_id: int,
    descricao: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> OfficioTemplateVersion:
    """
    Cria nova versão de modelo.
    Calcula versao_numero automaticamente: tipo='proposta' → v1.0, v2.0, v3.0, etc

    Args:
        db: Sessão do banco
        nome: Nome descritivo (ex: "Proposta Honorários")
        tipo: Tipo de ofício ('proposta', 'defesa', 'pagamento_final')
        conteudo_docx: Arquivo DOCX binário
        placeholders: Dict com placeholders encontrados
        created_by_id: ID do usuário criador
        descricao: Descrição opcional da versão
        tags: Tags opcionais para organização

    Returns:
        OfficioTemplateVersion criada

    Raises:
        ValueError: Se tipo inválido ou criador não encontrado
    """
    if tipo not in ('proposta', 'defesa', 'pagamento_final'):
        raise ValueError(f"Tipo inválido: {tipo}")

    # Valida usuário criador
    usuario = db.query(User).get(created_by_id)
    if not usuario:
        raise ValueError(f"Usuário {created_by_id} não encontrado")

    # Busca última versão ativa do tipo
    ultima_versao = (
        db.query(OfficioTemplateVersion)
        .filter(
            OfficioTemplateVersion.tipo == tipo,
            OfficioTemplateVersion.is_ativa == True
        )
        .order_by(desc(OfficioTemplateVersion.versao_numero))
        .first()
    )

    novo_numero = (ultima_versao.versao_numero if ultima_versao else 0) + 1
    versao_string = f"v{novo_numero}.0"

    nova_versao = OfficioTemplateVersion(
        id=str(uuid4()),
        nome=nome,
        tipo=tipo,
        versao_numero=novo_numero,
        versao_string=versao_string,
        conteudo_docx=conteudo_docx,
        placeholders=placeholders or {},
        created_by_id=created_by_id,
        is_ativa=True,
        descricao=descricao,
        tags=tags or [],
    )

    db.add(nova_versao)
    db.commit()
    db.refresh(nova_versao)

    logger.info(
        f"Nova versão de template criada: {versao_string} (tipo={tipo}, "
        f"criador={usuario.full_name}, id={nova_versao.id})"
    )

    return nova_versao


def listar_versoes_por_tipo(
    db: Session,
    tipo: str,
    incluir_inativas: bool = False,
) -> List[OfficioTemplateVersion]:
    """
    Retorna todas versões de um tipo, mais recentes primeiro.

    Args:
        db: Sessão do banco
        tipo: Tipo de ofício
        incluir_inativas: Se deve incluir versões deprecadas

    Returns:
        Lista de versões ordenadas por número descendente
    """
    query = db.query(OfficioTemplateVersion).filter(OfficioTemplateVersion.tipo == tipo)

    if not incluir_inativas:
        query = query.filter(OfficioTemplateVersion.is_ativa == True)

    return query.order_by(desc(OfficioTemplateVersion.versao_numero)).all()


def obter_versao_ativa(db: Session, tipo: str) -> Optional[OfficioTemplateVersion]:
    """
    Retorna versão ativa mais recente de um tipo.

    Args:
        db: Sessão do banco
        tipo: Tipo de ofício

    Returns:
        OfficioTemplateVersion ativa mais recente ou None
    """
    return (
        db.query(OfficioTemplateVersion)
        .filter(
            OfficioTemplateVersion.tipo == tipo,
            OfficioTemplateVersion.is_ativa == True,
        )
        .order_by(desc(OfficioTemplateVersion.versao_numero))
        .first()
    )


def obter_versao_por_id(
    db: Session,
    versao_id: str,
) -> Optional[OfficioTemplateVersion]:
    """
    Obtém uma versão específica pelo ID.

    Args:
        db: Sessão do banco
        versao_id: UUID da versão

    Returns:
        OfficioTemplateVersion ou None
    """
    return db.query(OfficioTemplateVersion).get(versao_id)


def deprecar_versao(
    db: Session,
    versao_id: str,
    updated_by_id: int,
) -> OfficioTemplateVersion:
    """
    Marca versão como inativa (deprecada), mas mantém histórico e ofícios associados.

    Args:
        db: Sessão do banco
        versao_id: UUID da versão
        updated_by_id: ID do usuário que está deprecando

    Returns:
        OfficioTemplateVersion deprecada

    Raises:
        ValueError: Se versão não encontrada
    """
    versao = db.query(OfficioTemplateVersion).get(versao_id)
    if not versao:
        raise ValueError(f"Versão {versao_id} não encontrada")

    versao.is_ativa = False
    versao.updated_by_id = updated_by_id
    versao.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(versao)

    logger.info(
        f"Versão de template deprecada: {versao.versao_string} "
        f"(tipo={versao.tipo}, id={versao.id})"
    )

    return versao


def obter_historico_versoes(db: Session, tipo: str) -> List[Dict[str, Any]]:
    """
    Retorna árvore histórica de versões: v1.0 → v1.1 → v2.0 → v2.1

    Args:
        db: Sessão do banco
        tipo: Tipo de ofício

    Returns:
        Lista de dicts com informações de cada versão (cronológica descendente)
    """
    versoes = listar_versoes_por_tipo(db, tipo, incluir_inativas=True)

    historico = []
    for v in reversed(versoes):  # Inverte para colocarem cronológico ascendente
        criador = v.created_by
        atualizador = v.updated_by

        historico.append({
            'id': v.id,
            'versao': v.versao_string,
            'nome': v.nome,
            'criada_por': criador.full_name if criador else 'Sistema',
            'criada_em': v.created_at.isoformat() if v.created_at else None,
            'atualizada_por': atualizador.full_name if atualizador else None,
            'atualizada_em': v.updated_at.isoformat() if v.updated_at else None,
            'ativa': v.is_ativa,
            'descricao': v.descricao,
            'tags': v.tags or [],
            'num_placeholders': len(v.placeholders) if v.placeholders else 0,
        })

    return historico


def contar_oficios_usando_versao(
    db: Session,
    versao_id: str,
) -> int:
    """
    Conta quantos ofícios estão usando uma versão específica.

    Args:
        db: Sessão do banco
        versao_id: UUID da versão

    Returns:
        Número de ofícios usando essa versão
    """
    from app.models import Oficio

    return db.query(Oficio).filter(Oficio.template_version_id == versao_id).count()


def validar_versao_para_deprecacao(
    db: Session,
    versao_id: str,
) -> Dict[str, Any]:
    """
    Valida se uma versão pode ser deprecada e retorna informações úteis.

    Args:
        db: Sessão do banco
        versao_id: UUID da versão

    Returns:
        Dict com status de validação e avisos

    Raises:
        ValueError: Se versão não encontrada
    """
    versao = db.query(OfficioTemplateVersion).get(versao_id)
    if not versao:
        raise ValueError(f"Versão {versao_id} não encontrada")

    if not versao.is_ativa:
        return {
            'pode_deprecar': False,
            'motivo': 'Versão já está inativa',
            'avisos': [],
        }

    num_oficios = contar_oficios_usando_versao(db, versao_id)
    avisos = []

    if num_oficios > 0:
        avisos.append(
            f'{num_oficios} ofício(s) estão usando esta versão e continuarão funcionando'
        )

    # Verifica se existe versão ativa de backup
    outras_ativas = (
        db.query(OfficioTemplateVersion)
        .filter(
            OfficioTemplateVersion.tipo == versao.tipo,
            OfficioTemplateVersion.is_ativa == True,
            OfficioTemplateVersion.id != versao_id,
        )
        .count()
    )

    if outras_ativas == 0:
        avisos.append(
            'Esta é a última versão ativa do tipo. '
            'Recomenda-se criar uma nova antes de deprecar.'
        )

    return {
        'pode_deprecar': True,
        'avisos': avisos,
        'num_oficios_usando': num_oficios,
        'tem_backup_ativa': outras_ativas > 0,
    }


def listar_tipos_disponíveis(db: Session) -> List[str]:
    """
    Retorna lista de tipos de ofício com pelo menos uma versão.

    Args:
        db: Sessão do banco

    Returns:
        Lista de tipos disponíveis
    """
    tipos = (
        db.query(OfficioTemplateVersion.tipo)
        .distinct()
        .order_by(OfficioTemplateVersion.tipo)
        .all()
    )
    return [t[0] for t in tipos]


def obter_estatisticas_templates(db: Session) -> Dict[str, Any]:
    """
    Retorna estatísticas globais de templates.

    Args:
        db: Sessão do banco

    Returns:
        Dict com estatísticas
    """
    from app.models import Oficio

    total_versoes = db.query(OfficioTemplateVersion).count()
    versoes_ativas = db.query(OfficioTemplateVersion).filter(
        OfficioTemplateVersion.is_ativa == True
    ).count()
    tipos = listar_tipos_disponíveis(db)

    estatisticas_por_tipo = {}
    for tipo in tipos:
        versoes = listar_versoes_por_tipo(db, tipo, incluir_inativas=True)
        versao_ativa = obter_versao_ativa(db, tipo)
        oficial_usando = db.query(Oficio).filter(
            Oficio.template_version_id.in_([v.id for v in versoes])
        ).count()

        estatisticas_por_tipo[tipo] = {
            'total_versoes': len(versoes),
            'versao_ativa': versao_ativa.versao_string if versao_ativa else None,
            'oficios_usando': oficial_usando,
        }

    return {
        'total_versoes': total_versoes,
        'versoes_ativas': versoes_ativas,
        'versoes_inativas': total_versoes - versoes_ativas,
        'tipos_disponiveis': tipos,
        'por_tipo': estatisticas_por_tipo,
    }
