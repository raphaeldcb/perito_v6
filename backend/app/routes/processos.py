"""Gestão de processos (perícias) — listar, ver detalhes, intimações e análise IA.

Esta é a tela central de trabalho: cada processo com suas intimações, o que a
IA extraiu (prazo, tipo, partes), status, e ações (baixar autos, emitir nota).
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, Processo, Intimacao, NotaFiscal, MovimentoProcesso, SetorPericia
from app.database import get_db
from app.services import ipca
from app.middleware.rate_limiting import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/processos", tags=["processos"])


@router.get("")
@limiter.limit(RATE_LIMITS["api_default"])
async def listar_processos(
    request: Request,
    busca: str = "",
    periodo: str = Query("", description="month|all"),
    setor: str = Query(""),
    status: str = Query(""),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Processo)  # Todos veem todos os processos

    # Busca textual
    if busca:
        like = f"%{busca}%"
        q = q.filter(
            (Processo.numero_cnj.ilike(like))
            | (Processo.titulo.ilike(like))
            | (Processo.autor.ilike(like))
            | (Processo.reu.ilike(like))
        )

    # Filtros
    if setor:
        q = q.filter(Processo.setor == setor)
    if status:
        q = q.filter(Processo.status == status)
    if periodo == "month":
        month_ago = datetime.utcnow() - timedelta(days=30)
        q = q.filter(Processo.created_at >= month_ago)

    total = q.count()
    processos = q.order_by(Processo.id.desc()).offset(skip).limit(limit).all()

    # Bulk load intimações e notas (evita N+1)
    processo_ids = [p.id for p in processos]
    if not processo_ids:
        return {"total": total, "itens": []}

    intimacoes_map = {}
    for i in db.query(Intimacao).filter(Intimacao.processo_id.in_(processo_ids)).all():
        if i.processo_id not in intimacoes_map:
            intimacoes_map[i.processo_id] = []
        intimacoes_map[i.processo_id].append(i)

    notas_map = {}
    for n in db.query(NotaFiscal).filter(
        NotaFiscal.processo_id.in_(processo_ids),
        NotaFiscal.status != "cancelada"
    ).all():
        notas_map[n.processo_id] = True

    resultado = []
    for p in processos:
        intimacoes = intimacoes_map.get(p.id, [])
        pendentes = sum(1 for i in intimacoes if i.status in ("pendente", "processando"))
        tem_nota = notas_map.get(p.id, False)
        resultado.append({
            "id": p.id, "numero_cnj": p.numero_cnj, "titulo": p.titulo,
            "autor": p.autor, "reu": p.reu, "vara": p.vara, "tribunal": p.tribunal,
            "especialidade": p.especialidade, "setor": p.setor, "status": p.status,
            "source_system": p.source_system,
            "doc": p.doc, "tipo": p.tipo, "responsavel": p.responsavel,
            "honorarios": float(p.honorarios) if p.honorarios is not None else None,
            "prazo": p.prazo.isoformat() if p.prazo else None,
            "intimacoes": len(intimacoes), "intimacoes_pendentes": pendentes,
            "tem_nota": tem_nota,
        })

    # FIX #4: Adicionar paginação explícita + warning se truncado
    warning = None
    if total > limit:
        warning = f"Resultados truncados: exibindo {len(resultado)}/{total}. Use skip/limit para navegar."

    return {
        "total": total,
        "limit": limit,
        "offset": skip,
        "count": len(resultado),
        "warning": warning,
        "itens": resultado,
    }


@router.get("/{processo_id}")
@limiter.limit(RATE_LIMITS["api_default"])
async def detalhe_processo(
    request: Request,
    processo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    intimacoes = (
        db.query(Intimacao)
        .filter(Intimacao.processo_id == processo_id)
        .order_by(Intimacao.id.desc())
        .all()
    )
    notas = db.query(NotaFiscal).filter(NotaFiscal.processo_id == processo_id).all()
    movimentos = db.query(MovimentoProcesso).filter(
        MovimentoProcesso.processo_id == processo_id).order_by(MovimentoProcesso.data).all()

    total_despesas = sum(float(m.valor) for m in movimentos if m.tipo == "despesa")
    total_entradas = sum(float(m.valor) for m in movimentos if m.tipo == "entrada")

    # custo real com IPCA: honorários corrigidos da data de aceite até hoje (ou pagamento)
    custo_ipca = None
    if p.honorarios and p.data_aceite:
        data_fim = p.data_pagamento or None
        custo_ipca = ipca.corrigir(float(p.honorarios), p.data_aceite, data_fim)

    return {
        "id": p.id, "numero_cnj": p.numero_cnj, "titulo": p.titulo,
        "descricao": p.descricao, "autor": p.autor, "reu": p.reu,
        "vara": p.vara, "tribunal": p.tribunal, "juiz": p.juiz,
        "especialidade": p.especialidade, "status": p.status,
        "honorarios": float(p.honorarios) if p.honorarios is not None else None,
        "forma_recebimento": p.forma_recebimento, "pago": p.pago,
        "data_aceite": p.data_aceite.isoformat() if p.data_aceite else None,
        "data_pagamento": p.data_pagamento.isoformat() if p.data_pagamento else None,
        "financeiro": {
            "total_despesas": round(total_despesas, 2),
            "total_entradas": round(total_entradas, 2),
            "saldo": round(total_entradas - total_despesas, 2),
            "movimentos": [
                {"id": m.id, "tipo": m.tipo, "categoria": m.categoria, "descricao": m.descricao,
                 "valor": float(m.valor), "data": m.data.isoformat() if m.data else None}
                for m in movimentos
            ],
            "custo_ipca": custo_ipca,
        },
        "source_system": p.source_system, "external_id": p.external_id,
        "intimacoes": [
            {
                "id": i.id, "origem": i.origem, "tipo": i.tipo, "assunto": i.assunto,
                "status": i.status, "pdf_path": i.pdf_path,
                "dados_estruturados": i.dados_estruturados, "erros": i.erros,
                "criado_em": i.created_at.isoformat() if i.created_at else None,
            }
            for i in intimacoes
        ],
        "notas": [
            {"id": n.id, "status": n.status, "numero_nfse": n.numero_nfse,
             "numero_rps": n.numero_rps, "valor": float(n.valor_servico) if n.valor_servico else None}
            for n in notas
        ],
    }


class ProcessoUpdate(BaseModel):
    numero_cnj: str | None = None
    empresa_id: int | None = None
    tipo_pericia: str | None = None  # Judicial, Extrajudicial, DNA
    setor: str | None = None  # 01-Contábil, 02-Engenharia
    status: str | None = None  # Protocolado, Em Andamento, Concluído
    prioridade: str | None = None  # Baixa, Média, Alta
    comarca: str | None = None
    vara: str | None = None
    juiz: str | None = None
    partes: list | None = None  # [{papel, nome, doc}, ...]
    participantes_dna: list | None = None
    laboratorio: str | None = None
    deslocamento: dict | None = None
    documentos: list | None = None
    # Campos legados
    titulo: str | None = None
    especialidade: str | None = None
    autor: str | None = None
    reu: str | None = None
    doc: str | None = None
    tipo: str | None = None
    responsavel: str | None = None
    honorarios: float | None = None
    prazo: str | None = None  # ISO date

    @field_validator("setor")
    @classmethod
    def validar_setor(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        if v not in SetorPericia.valores():
            raise ValueError(
                f"setor inválido: '{v}'. Use um de {SetorPericia.valores()} (ver SETORES.md)"
            )
        return v


@router.patch("/{processo_id}")
async def atualizar_processo(
    processo_id: int,
    payload: ProcessoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """FIX #8: Auth bypass — verificar empresa_id antes de atualizar.

    User A NÃO pode editar processo que pertence a User B.
    Se empresa_id não está setado, assume que a empresa do usuário é a dona.
    """
    from datetime import datetime as _dt
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    # Verify authorization: user can only edit processes in their company
    if p.empresa_id and user.empresa_id and p.empresa_id != user.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado: processo pertence a outra empresa")

    for campo, valor in payload.model_dump(exclude_unset=True).items():
        if valor is None:
            continue
        # Don't allow changing empresa_id from outside (privilege escalation)
        if campo == "empresa_id":
            logger.warning(f"🚨 User {user.id} tentou mudar empresa_id do processo {processo_id}")
            continue
        if campo == "prazo":
            try:
                p.prazo = _dt.fromisoformat(str(valor)[:19])
            except ValueError:
                pass
        else:
            setattr(p, campo, valor)
    db.commit()
    return {"ok": True}


class ProcessoCreate(BaseModel):
    numero_cnj: str
    empresa_id: int
    tipo_pericia: str = "Extrajudicial"  # Judicial, Extrajudicial, DNA
    setor: str  # OBRIGATÓRIO — nome do setor (Contábil/DNA/Engenharia/Grafotécnica/Multidisciplinar/Declina)
    status: str = "Protocolado"  # Protocolado, Em Andamento, Concluído
    prioridade: str = "Média"  # Baixa, Média, Alta
    comarca: str | None = None
    vara: str | None = None
    juiz: str | None = None
    partes: list | None = None  # [{papel, nome, doc}, ...]
    participantes_dna: list | None = None
    laboratorio: str | None = None
    # Campos legados
    titulo: str | None = None
    autor: str | None = None
    reu: str | None = None
    especialidade: str | None = None

    @field_validator("setor")
    @classmethod
    def validar_setor(cls, v: str) -> str:
        if v not in SetorPericia.valores():
            raise ValueError(
                f"setor inválido: '{v}'. Use um de {SetorPericia.valores()} (ver SETORES.md)"
            )
        return v


@router.post("")
async def criar_processo(
    payload: ProcessoCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.query(Processo).filter(Processo.numero_cnj == payload.numero_cnj).first():
        raise HTTPException(status_code=400, detail="Já existe processo com esse número")
    p = Processo(
        numero_cnj=payload.numero_cnj.strip(),
        empresa_id=payload.empresa_id,
        tipo_pericia=payload.tipo_pericia,
        setor=payload.setor,
        status=payload.status,
        prioridade=payload.prioridade,
        comarca=payload.comarca,
        vara=payload.vara,
        juiz=payload.juiz,
        partes=payload.partes or [],
        participantes_dna=payload.participantes_dna or [],
        laboratorio=payload.laboratorio,
        # Campos legados para compatibilidade
        titulo=payload.titulo or f"Processo {payload.numero_cnj}",
        autor=payload.autor,
        reu=payload.reu,
        source_system="manual",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "id": p.id,
        "numero_cnj": p.numero_cnj,
        "empresa_id": p.empresa_id,
        "comarca": p.comarca,
        "vara": p.vara,
        "juiz": p.juiz,
    }


@router.post("/reprocessar-vinculos")
async def reprocessar_vinculos(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-sincroniza cadastro dos processos a partir das intimações já analisadas.
    Preenche autor/reu/vara/juiz vazios sem sobrescrever edição manual.
    Serve para backfill e para reconciliar sistemas legados (Passo 2)."""
    from app.services import vinculo
    intimacoes = db.query(Intimacao).filter(
        Intimacao.dados_estruturados.isnot(None),
        Intimacao.processo_id.isnot(None),
    ).all()
    tocados = 0
    for i in intimacoes:
        proc = db.query(Processo).filter(Processo.id == i.processo_id).first()
        if proc and vinculo.propagar(proc, i.dados_estruturados):
            tocados += 1
    db.commit()
    return {"intimacoes_analisadas": len(intimacoes), "processos_atualizados": tocados}


class MovimentoCreate(BaseModel):
    tipo: str            # despesa | entrada
    categoria: str | None = None
    descricao: str | None = None
    valor: float
    data: str | None = None  # ISO date


@router.post("/{processo_id}/movimentos")
async def add_movimento(
    processo_id: int,
    payload: MovimentoCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lança uma despesa ou entrada no processo (deslocamento, vistoria, custas...)."""
    from datetime import datetime as _dt, date as _date
    if not db.query(Processo).filter(Processo.id == processo_id).first():
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    if payload.tipo not in ("despesa", "entrada"):
        raise HTTPException(status_code=400, detail="tipo deve ser 'despesa' ou 'entrada'")
    data = None
    if payload.data:
        try:
            data = _dt.fromisoformat(payload.data[:10]).date()
        except ValueError:
            pass
    m = MovimentoProcesso(
        processo_id=processo_id, tipo=payload.tipo, categoria=payload.categoria,
        descricao=payload.descricao, valor=payload.valor, data=data or _date.today(),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id}


@router.delete("/{processo_id}/movimentos/{mov_id}")
async def del_movimento(
    processo_id: int, mov_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    m = db.query(MovimentoProcesso).filter(
        MovimentoProcesso.id == mov_id, MovimentoProcesso.processo_id == processo_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")
    db.delete(m)
    db.commit()
    return {"ok": True}


class RecebimentoUpdate(BaseModel):
    honorarios: float | None = None
    forma_recebimento: str | None = None   # a_vista, ao_final, judicial
    data_aceite: str | None = None
    pago: bool | None = None
    data_pagamento: str | None = None


@router.patch("/{processo_id}/recebimento")
async def atualizar_recebimento(
    processo_id: int,
    payload: RecebimentoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import datetime as _dt
    p = db.query(Processo).filter(Processo.id == processo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    dados = payload.model_dump(exclude_unset=True)
    if "honorarios" in dados and dados["honorarios"] is not None:
        p.honorarios = dados["honorarios"]
    if "forma_recebimento" in dados:
        p.forma_recebimento = dados["forma_recebimento"]
    if "pago" in dados and dados["pago"] is not None:
        p.pago = dados["pago"]
    for campo in ("data_aceite", "data_pagamento"):
        if dados.get(campo):
            try:
                setattr(p, campo, _dt.fromisoformat(str(dados[campo])[:19]))
            except ValueError:
                pass
    db.commit()
    return {"ok": True}
