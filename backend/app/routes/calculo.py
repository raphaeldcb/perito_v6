"""Calculadora de atualização monetária — ferramenta pericial (aba Ferramentas).

Motor 100% determinístico (services/calculo_atualizacao). O Qwen só SUGERE os
critérios lendo a decisão (POST /interpretar-decisao).
"""
import io
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.middleware import get_current_user
from app.models import User, IndiceCustomizado, Job, Processo, PadraoCalculo, Calculo, CalculoVinculo, CalculoHistorico
from app.services import get_db, indices_bcb, calculo_atualizacao, honorarios, deslocamento
from app.services.calculo_diff import calcular_diff
from app.decorators.require_feature import require_feature_flag

router = APIRouter(prefix="/api/v1/calculo", tags=["calculo"])


@router.get("/indices")
async def listar_indices(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    custom = db.query(IndiceCustomizado).filter(IndiceCustomizado.usuario_id == user.id).all()
    return {
        "oficiais": indices_bcb.listar(),
        "customizados": [{"id": c.id, "nome": c.nome} for c in custom],
    }


class Periodo(BaseModel):
    inicio: str
    fim: str | None = None
    indexador: str | None = None
    regime: str = "indice_mais_juros"   # indice_mais_juros | selic | customizado
    juros_remun_am: float = 0.0
    juros_mora_am: float = 0.0
    indice_customizado_nome: str | None = None


class Pagamento(BaseModel):
    data: str
    valor: float


class CalculoInput(BaseModel):
    valor: float
    data_inicial: str
    data_final: str | None = None
    timeline: list[Periodo]
    base_dias: int = 365
    pagamentos: list[Pagamento] = []
    tese: str = "juros_primeiro"
    multa_pct: float = 0.0


def _rodar(payload: CalculoInput, db: Session, user: User) -> dict:
    custom = {c.nome: (c.valores or {})
              for c in db.query(IndiceCustomizado).filter(IndiceCustomizado.usuario_id == user.id).all()}
    return calculo_atualizacao.calcular(
        valor=payload.valor, data_inicial=payload.data_inicial, data_final=payload.data_final,
        timeline=[p.model_dump() for p in payload.timeline], base_dias=payload.base_dias,
        pagamentos=[p.model_dump() for p in payload.pagamentos], tese=payload.tese,
        multa_pct=payload.multa_pct, customizados=custom,
    )


@router.post("/calcular")
async def calcular(payload: CalculoInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return _rodar(payload, db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


COLS = ["Mês/Ano", "Valor Nominal", "% Correção", "Saldo Corrigido",
        "% Juros Remun.", "% Juros Mora", "% Multa", "Saldo Total"]


@router.post("/exportar")
async def exportar(payload: CalculoInput, formato: str = "xlsx",
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    res = _rodar(payload, db, user)
    linhas = [[l["mes_ano"], l["valor_nominal"], l["pct_correcao"], l["saldo_corrigido"],
               l["pct_juros_remun"], l["pct_juros_mora"], l["pct_multa"], l["saldo_total_mes"]]
              for l in res["linhas"]]

    if formato == "pdf":
        from fpdf import FPDF
        import unicodedata
        def a(s): return unicodedata.normalize("NFKD", str(s)).encode("latin-1", "ignore").decode("latin-1")
        pdf = FPDF(orientation="L"); pdf.add_page(); pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, a("Memoria de Calculo - Atualizacao Monetaria"), ln=True)
        pdf.set_font("Helvetica", "", 8)
        # Valores já vêm formatados em PT-BR (ex: "R$ 1.234,56"), não adicionar "R$ " novamente
        pdf.cell(0, 6, a(f"Valor original: {res['totais']['valor_original']}  |  Saldo final: {res['totais']['saldo_final']}"), ln=True)
        pdf.set_font("Helvetica", "B", 7); larg = (pdf.w - 20) / len(COLS)
        for c in COLS: pdf.cell(larg, 6, a(c), border=1)
        pdf.ln(); pdf.set_font("Helvetica", "", 7)
        for linha in linhas:
            for v in linha: pdf.cell(larg, 5, a(v), border=1)
            pdf.ln()
        buf = io.BytesIO(pdf.output()); buf.seek(0)
        return StreamingResponse(buf, media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="calculo_atualizacao.pdf"'})

    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "Atualizacao"
    ws.append(COLS)
    for linha in linhas:
        ws.append(linha)
    ws.append([])
    ws.append(["", "", "", "", "", "", "TOTAL", res["totais"]["saldo_final"]])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="calculo_atualizacao.xlsx"'})


class IndiceCustomInput(BaseModel):
    nome: str
    valores: dict   # {"AAAA-MM": pct}


@router.post("/indices-customizados")
async def criar_indice_custom(payload: IndiceCustomInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ic = db.query(IndiceCustomizado).filter(
        IndiceCustomizado.usuario_id == user.id, IndiceCustomizado.nome == payload.nome).first()
    if ic:
        ic.valores = payload.valores
    else:
        ic = IndiceCustomizado(usuario_id=user.id, nome=payload.nome, valores=payload.valores)
        db.add(ic)
    db.commit()
    return {"ok": True, "nome": payload.nome}


class HonorariosInput(BaseModel):
    valor_caso: float
    tipo_imposto: str = "direto"
    parcelas: int = 12
    sem_imposto: bool = False


class HonorariosCombinadoInput(BaseModel):
    alocacoes: dict            # {dinheiro, pix, debito, credito, parcelado} em R$ líquido
    tipo_imposto: str = "direto"
    parcelas: int = 12
    sem_imposto: bool = False


@router.post("/honorarios")
async def calc_honorarios(payload: HonorariosInput, user: User = Depends(get_current_user)):
    """Precificação (TABELA CALCULO PERÍCIA): valor → PIX/débito/crédito/parcelado."""
    return honorarios.calcular(payload.valor_caso, payload.tipo_imposto, payload.parcelas,
                               sem_imposto=payload.sem_imposto)


@router.post("/honorarios/combinado")
async def calc_honorarios_combinado(payload: HonorariosCombinadoInput,
                                    user: User = Depends(get_current_user)):
    """Combina várias formas de pagamento numa cobrança só (dinheiro+pix+débito+crédito+parcelado)."""
    return honorarios.calcular_combinado(payload.alocacoes, payload.tipo_imposto,
                                         payload.parcelas, sem_imposto=payload.sem_imposto)


@router.get("/deslocamento/cidades")
async def desloc_cidades(user: User = Depends(get_current_user)):
    return deslocamento.cidades()


class DeslocamentoInput(BaseModel):
    distancia_km: float
    tipo_via: str = "asfalto"
    pedagios: Optional[float] = None  # None = calcular via API
    ida_volta: bool = True
    origem: Optional[str] = None  # Pra calcular pedágio
    destino: Optional[str] = None


@router.post("/deslocamento")
async def calc_deslocamento(payload: DeslocamentoInput, user: User = Depends(get_current_user)):
    """Custo de deslocamento: km × custo/km + pedágio (ida/volta)."""

    pedagios = payload.pedagios

    # Se não informou pedágio manualmente, calcula via API
    if pedagios is None and payload.origem and payload.destino:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"/api/v1/deslocamento/pedagio",
                    params={"origem": payload.origem, "destino": payload.destino}
                )
                pedagios = resp.json()["pedagio_total"]
        except:
            pedagios = 0.0  # Fallback se API falhar
    else:
        pedagios = pedagios or 0.0

    return deslocamento.calcular(payload.distancia_km, payload.tipo_via,
                                 pedagios, payload.ida_volta)


class PadraoInput(BaseModel):
    nome: str
    config: dict


@router.get("/padroes")
async def listar_padroes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ps = db.query(PadraoCalculo).filter(PadraoCalculo.usuario_id == user.id).order_by(PadraoCalculo.nome).all()
    return [{"id": p.id, "nome": p.nome, "config": p.config} for p in ps]


@router.post("/padroes")
async def salvar_padrao(payload: PadraoInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.query(PadraoCalculo).filter(PadraoCalculo.usuario_id == user.id, PadraoCalculo.nome == payload.nome).first()
    if p:
        p.config = payload.config
    else:
        p = PadraoCalculo(usuario_id=user.id, nome=payload.nome, config=payload.config)
        db.add(p)
    db.commit(); db.refresh(p)
    return {"id": p.id, "nome": p.nome}


@router.delete("/padroes/{padrao_id}")
async def excluir_padrao(padrao_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.query(PadraoCalculo).filter(PadraoCalculo.id == padrao_id, PadraoCalculo.usuario_id == user.id).first()
    if p:
        db.delete(p); db.commit()
    return {"ok": True}


class InterpretarInput(BaseModel):
    texto: str


@router.post("/interpretar-decisao")
async def interpretar_decisao(payload: InterpretarInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Qwen 3.6 lê a decisão e SUGERE a linha do tempo de critérios (o perito confirma)."""
    if not payload.texto.strip():
        raise HTTPException(status_code=400, detail="Cole o trecho da decisão")
    job = Job(tipo="interpretar_decisao", status="na_fila",
              payload={"texto": payload.texto[:8000]})
    db.add(job); db.commit(); db.refresh(job)
    return {"job_id": job.id, "mensagem": "Qwen analisando a decisão para sugerir os critérios."}


class VincularInput(BaseModel):
    calculo_id: int
    tipo_vinculo: str  # laudo | proposta | at
    objeto_id: int


def _saldo_final_numerico(resultado: dict | None) -> float | None:
    """Extrai o saldo final do JSON de resultado do cálculo, aceitando tanto
    float cru quanto string formatada PT-BR ('R$ 1.234,56', ver Task 2)."""
    if not isinstance(resultado, dict):
        return None
    valor = (resultado.get("totais") or {}).get("saldo_final")
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


@router.post("/vincular")
async def vincular_calculo(payload: VincularInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Vincula um cálculo já salvo a um laudo/proposta/AT e abre o histórico
    de versões com a V1 (estado do cálculo no momento do vínculo)."""
    if payload.tipo_vinculo not in ("laudo", "proposta", "at"):
        raise HTTPException(status_code=400, detail="tipo_vinculo inválido (laudo | proposta | at)")

    calculo = db.query(Calculo).filter(Calculo.id == payload.calculo_id).first()
    if not calculo:
        raise HTTPException(status_code=404, detail="Cálculo não encontrado")

    existente = db.query(CalculoVinculo).filter(CalculoVinculo.calculo_id == payload.calculo_id).first()
    if existente:
        raise HTTPException(status_code=400, detail="Cálculo já vinculado")

    vinculo = CalculoVinculo(
        calculo_id=payload.calculo_id,
        tipo_vinculo=payload.tipo_vinculo,
        objeto_id=payload.objeto_id,
        versao=1,
    )
    db.add(vinculo)
    db.flush()

    historico = CalculoHistorico(
        calculo_id=payload.calculo_id,
        versao=1,
        payload=calculo.payload,
        resultado_saldo_final=_saldo_final_numerico(calculo.resultado),
        criado_por=user.id,
        alteracao_descricao="Criado e vinculado",
    )
    db.add(historico)
    db.commit()

    return {
        "vinculo_id": vinculo.id,
        "tipo_vinculo": vinculo.tipo_vinculo,
        "versao": vinculo.versao,
    }


@router.get("/{calculo_id}/historico")
async def get_historico(calculo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Timeline de versões de um cálculo vinculado (Task 5). 403 tanto se o
    cálculo não existe quanto se não é do usuário — não diferencia pra não
    vazar existência de cálculo alheio (mesma proteção anti-IDOR do plano)."""
    calculo = db.query(Calculo).filter(Calculo.id == calculo_id).first()
    if not calculo or calculo.usuario_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    historico = (db.query(CalculoHistorico)
                 .filter(CalculoHistorico.calculo_id == calculo_id)
                 .order_by(CalculoHistorico.versao.asc())
                 .all())

    return [
        {
            "versao": h.versao,
            "saldo_final": float(h.resultado_saldo_final) if h.resultado_saldo_final is not None else None,
            "criado_em": h.criado_em.isoformat() if h.criado_em else None,
            "alteracao_descricao": h.alteracao_descricao,
        }
        for h in historico
    ]


@router.post("/{calculo_id}/atualizar")
async def atualizar_calculo(calculo_id: int, payload: CalculoInput,
                            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Recalcula um cálculo já vinculado, cria a próxima versão no histórico
    e devolve o diff visual (V-anterior → V-nova). 404 tanto se o cálculo não
    existe quanto se não é do usuário (mesma proteção anti-IDOR do GET
    /historico)."""
    calculo = db.query(Calculo).filter(Calculo.id == calculo_id, Calculo.usuario_id == user.id).first()
    if not calculo:
        raise HTTPException(status_code=404, detail="Cálculo não encontrado")

    vinculo = db.query(CalculoVinculo).filter(CalculoVinculo.calculo_id == calculo_id).first()
    if not vinculo:
        raise HTTPException(status_code=400, detail="Cálculo não está vinculado")

    historico_anterior = (db.query(CalculoHistorico)
                          .filter(CalculoHistorico.calculo_id == calculo_id,
                                  CalculoHistorico.versao == vinculo.versao)
                          .first())
    if not historico_anterior:
        raise HTTPException(status_code=400, detail="Versão anterior não encontrada no histórico")

    try:
        novo_resultado = _rodar(payload, db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    saldo_v1 = float(historico_anterior.resultado_saldo_final or 0)
    saldo_v2 = _saldo_final_numerico(novo_resultado) or 0.0
    diff = calcular_diff(saldo_v1, saldo_v2)

    nova_versao = vinculo.versao + 1
    historico_novo = CalculoHistorico(
        calculo_id=calculo_id,
        versao=nova_versao,
        payload=payload.model_dump(),
        resultado_saldo_final=Decimal(str(saldo_v2)),
        criado_por=user.id,
        alteracao_descricao="Atualizado",
    )
    db.add(historico_novo)

    calculo.payload = payload.model_dump()
    calculo.resultado = novo_resultado
    calculo.atualizado_em = datetime.utcnow()

    vinculo.versao = nova_versao
    vinculo.atualizado_em = datetime.utcnow()

    db.commit()

    return {
        "nova_versao": nova_versao,
        "diff": diff,
    }
