"""
ProjetoCP Services — Lógica de negócio para Processo, Comarca, Vara, Juiz.

PHASE 1: CRUD e validações
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List, Tuple
from app.models.projetocp import (
    Comarca, Vara, Juiz,
    StatusComarca, StatusVara, StatusJuiz, StatusProcesso
)
from app.models.processo import Processo
from app.schemas.projetocp import (
    ComarcaCreate, ComarcaUpdate,
    VaraCreate, VaraUpdate,
    JuizCreate, JuizUpdate,
    ProcessoCreate, ProcessoUpdate, ProcessoRead
)


class ComarcaService:
    """Service para gerenciar Comarcas."""

    @staticmethod
    def criar(db: Session, comarca: ComarcaCreate) -> Comarca:
        """Criar nova Comarca."""
        db_comarca = Comarca(
            nome=comarca.nome,
            codigo_cnj=comarca.codigo_cnj,
            uf=comarca.uf,
            municipio=comarca.municipio,
            status=comarca.status,
        )
        db.add(db_comarca)
        db.commit()
        db.refresh(db_comarca)
        return db_comarca

    @staticmethod
    def obter_por_id(db: Session, comarca_id: int) -> Optional[Comarca]:
        """Obter Comarca por ID."""
        return db.query(Comarca).filter(Comarca.id == comarca_id).first()

    @staticmethod
    def obter_por_nome(db: Session, nome: str) -> Optional[Comarca]:
        """Obter Comarca por nome (case-insensitive)."""
        return db.query(Comarca).filter(Comarca.nome.ilike(nome)).first()

    @staticmethod
    def listar(db: Session, skip: int = 0, limit: int = 50, uf: Optional[str] = None) -> Tuple[int, List[Comarca]]:
        """Listar Comarcas com filtros opcionais."""
        query = db.query(Comarca)
        if uf:
            query = query.filter(Comarca.uf == uf.upper())
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def atualizar(db: Session, comarca_id: int, update: ComarcaUpdate) -> Optional[Comarca]:
        """Atualizar Comarca."""
        db_comarca = ComarcaService.obter_por_id(db, comarca_id)
        if not db_comarca:
            return None

        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_comarca, field, value)

        db.commit()
        db.refresh(db_comarca)
        return db_comarca

    @staticmethod
    def deletar(db: Session, comarca_id: int) -> bool:
        """Deletar Comarca (soft delete: marcar como inativa)."""
        db_comarca = ComarcaService.obter_por_id(db, comarca_id)
        if not db_comarca:
            return False

        db_comarca.status = StatusComarca.INATIVO
        db.commit()
        return True


class VaraService:
    """Service para gerenciar Varas."""

    @staticmethod
    def criar(db: Session, vara: VaraCreate) -> Vara:
        """Criar nova Vara."""
        db_vara = Vara(
            comarca_id=vara.comarca_id,
            nome=vara.nome,
            codigo_cnj=vara.codigo_cnj,
            tipo=vara.tipo,
            status=vara.status,
            observacoes=vara.observacoes,
        )
        db.add(db_vara)
        db.commit()
        db.refresh(db_vara)
        return db_vara

    @staticmethod
    def obter_por_id(db: Session, vara_id: int) -> Optional[Vara]:
        """Obter Vara por ID."""
        return db.query(Vara).filter(Vara.id == vara_id).first()

    @staticmethod
    def listar(db: Session, comarca_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> Tuple[int, List[Vara]]:
        """Listar Varas com filtros opcionais."""
        query = db.query(Vara)
        if comarca_id:
            query = query.filter(Vara.comarca_id == comarca_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def atualizar(db: Session, vara_id: int, update: VaraUpdate) -> Optional[Vara]:
        """Atualizar Vara."""
        db_vara = VaraService.obter_por_id(db, vara_id)
        if not db_vara:
            return None

        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_vara, field, value)

        db.commit()
        db.refresh(db_vara)
        return db_vara

    @staticmethod
    def deletar(db: Session, vara_id: int) -> bool:
        """Deletar Vara (soft delete: marcar como inativa)."""
        db_vara = VaraService.obter_por_id(db, vara_id)
        if not db_vara:
            return False

        db_vara.status = StatusVara.INATIVO
        db.commit()
        return True


class JuizService:
    """Service para gerenciar Juizes."""

    @staticmethod
    def criar(db: Session, juiz: JuizCreate) -> Juiz:
        """Criar novo Juiz."""
        db_juiz = Juiz(
            comarca_id=juiz.comarca_id,
            vara_id=juiz.vara_id,
            nome=juiz.nome,
            cpf=juiz.cpf,
            registro_cnj=juiz.registro_cnj,
            email=juiz.email,
            telefone=juiz.telefone,
            status=juiz.status,
            observacoes=juiz.observacoes,
        )
        db.add(db_juiz)
        db.commit()
        db.refresh(db_juiz)
        return db_juiz

    @staticmethod
    def obter_por_id(db: Session, juiz_id: int) -> Optional[Juiz]:
        """Obter Juiz por ID."""
        return db.query(Juiz).filter(Juiz.id == juiz_id).first()

    @staticmethod
    def obter_por_nome(db: Session, nome: str) -> Optional[Juiz]:
        """Obter Juiz por nome (case-insensitive)."""
        return db.query(Juiz).filter(Juiz.nome.ilike(nome)).first()

    @staticmethod
    def listar(db: Session, comarca_id: Optional[int] = None, vara_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> Tuple[int, List[Juiz]]:
        """Listar Juizes com filtros opcionais."""
        query = db.query(Juiz)
        if comarca_id:
            query = query.filter(Juiz.comarca_id == comarca_id)
        if vara_id:
            query = query.filter(Juiz.vara_id == vara_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def atualizar(db: Session, juiz_id: int, update: JuizUpdate) -> Optional[Juiz]:
        """Atualizar Juiz."""
        db_juiz = JuizService.obter_por_id(db, juiz_id)
        if not db_juiz:
            return None

        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_juiz, field, value)

        db.commit()
        db.refresh(db_juiz)
        return db_juiz

    @staticmethod
    def deletar(db: Session, juiz_id: int) -> bool:
        """Deletar Juiz (soft delete: marcar como aposentado)."""
        db_juiz = JuizService.obter_por_id(db, juiz_id)
        if not db_juiz:
            return False

        db_juiz.status = StatusJuiz.APOSENTADO
        db.commit()
        return True


class ProcessoService:
    """Service para gerenciar Processos."""

    @staticmethod
    def criar(db: Session, processo: ProcessoCreate) -> Processo:
        """Criar novo Processo."""
        # Validar referências externas se fornecidas
        if processo.comarca_id:
            comarca = db.query(Comarca).filter(Comarca.id == processo.comarca_id).first()
            if not comarca:
                raise ValueError(f"Comarca {processo.comarca_id} não encontrada")

        if processo.vara_id:
            vara = db.query(Vara).filter(Vara.id == processo.vara_id).first()
            if not vara:
                raise ValueError(f"Vara {processo.vara_id} não encontrada")

        if processo.juiz_id:
            juiz = db.query(Juiz).filter(Juiz.id == processo.juiz_id).first()
            if not juiz:
                raise ValueError(f"Juiz {processo.juiz_id} não encontrado")

        db_processo = Processo(
            numero_cnj=processo.numero_cnj,
            empresa_id=processo.empresa_id,
            tipo=processo.tipo,
            tipo_pericia=processo.tipo_pericia,
            setor=processo.setor,
            status=processo.status,
            prioridade=processo.prioridade,
            comarca_id=processo.comarca_id,
            vara_id=processo.vara_id,
            juiz_id=processo.juiz_id,
            partes=processo.partes or [],
            participantes_dna=processo.participantes_dna or [],
            laboratorio=processo.laboratorio,
            deslocamento=processo.deslocamento,
            valor_causa=processo.valor_causa,
            documentos=processo.documentos or [],
            responsavel_id=processo.responsavel_id,
            observacoes=processo.observacoes,
        )
        db.add(db_processo)
        db.commit()
        db.refresh(db_processo)
        return db_processo

    @staticmethod
    def obter_por_id(db: Session, processo_id: int) -> Optional[Processo]:
        """Obter Processo por ID."""
        return db.query(Processo).filter(Processo.id == processo_id).first()

    @staticmethod
    def obter_por_numero_cnj(db: Session, numero_cnj: str) -> Optional[Processo]:
        """Obter Processo por número CNJ."""
        return db.query(Processo).filter(Processo.numero_cnj == numero_cnj).first()

    @staticmethod
    def listar(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        status: Optional[StatusProcesso] = None,
        comarca_id: Optional[int] = None,
        juiz_id: Optional[int] = None,
        responsavel_id: Optional[int] = None,
    ) -> Tuple[int, List[Processo]]:
        """Listar Processos com filtros opcionais."""
        query = db.query(Processo)

        if status:
            query = query.filter(Processo.status == status)
        if comarca_id:
            query = query.filter(Processo.comarca_id == comarca_id)
        if juiz_id:
            query = query.filter(Processo.juiz_id == juiz_id)
        if responsavel_id:
            query = query.filter(Processo.responsavel_id == responsavel_id)

        total = query.count()
        items = query.order_by(Processo.created_at.desc()).offset(skip).limit(limit).all()
        return total, items

    @staticmethod
    def atualizar(db: Session, processo_id: int, update: ProcessoUpdate) -> Optional[Processo]:
        """Atualizar Processo (partial)."""
        db_processo = ProcessoService.obter_por_id(db, processo_id)
        if not db_processo:
            return None

        # Validar referências externas se fornecidas no update
        if update.comarca_id:
            comarca = db.query(Comarca).filter(Comarca.id == update.comarca_id).first()
            if not comarca:
                raise ValueError(f"Comarca {update.comarca_id} não encontrada")

        if update.vara_id:
            vara = db.query(Vara).filter(Vara.id == update.vara_id).first()
            if not vara:
                raise ValueError(f"Vara {update.vara_id} não encontrada")

        if update.juiz_id:
            juiz = db.query(Juiz).filter(Juiz.id == update.juiz_id).first()
            if not juiz:
                raise ValueError(f"Juiz {update.juiz_id} não encontrado")

        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_processo, field, value)

        db.commit()
        db.refresh(db_processo)
        return db_processo

    @staticmethod
    def deletar(db: Session, processo_id: int) -> bool:
        """Deletar Processo (soft delete: marcar como cancelado/arquivado)."""
        db_processo = ProcessoService.obter_por_id(db, processo_id)
        if not db_processo:
            return False

        db_processo.status = StatusProcesso.CANCELADO
        db.commit()
        return True

    @staticmethod
    def contar_por_status(db: Session) -> dict:
        """Contar processos por status (para dashboard)."""
        result = {}
        for status in StatusProcesso:
            count = db.query(Processo).filter(Processo.status == status).count()
            result[status.value] = count
        return result
