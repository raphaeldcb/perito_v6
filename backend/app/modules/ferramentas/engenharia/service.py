"""Engenharia service — business logic for vistoria operations."""

from datetime import datetime
from pathlib import Path
import tempfile
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.models import ModeloVistoria, Vistoria, VistoriaFoto, Processo, User
from app.services.pdf_engenharia import gerar_pdf_vistoria
from app.services.laudo_qwen import gerar_laudo_vistoria, resumo_rpido_vistoria


def _vistoria_dict(v: Vistoria) -> dict:
    """Convert Vistoria ORM object to dict."""
    return {
        "id": v.id,
        "modelo_id": v.modelo_id,
        "modelo_versao": v.modelo_versao,
        "modelo_nome": v.modelo.nome if v.modelo else None,
        "processo_id": v.processo_id,
        "local": v.local,
        "gps": v.gps,
        "status": v.status,
        "dados": v.dados or {},
        "uuid_offline": v.uuid_offline,
        "pdf_path": v.pdf_path,
        "fotos": len(v.fotos),
        "assinaturas": len(v.assinaturas),
        "criado_em": v.created_at.isoformat() if v.created_at else None,
    }


# ============================================================================
# Modelos
# ============================================================================


def listar_modelos(db: Session, incluir_inativos: bool = False) -> List[dict]:
    """Lista todos os modelos de vistoria."""
    q = db.query(ModeloVistoria)
    if not incluir_inativos:
        q = q.filter(ModeloVistoria.ativo.is_(True))
    modelos = q.order_by(ModeloVistoria.nome).all()
    return [
        {
            "id": m.id,
            "area": m.area,
            "nome": m.nome,
            "descricao": m.descricao,
            "versao": m.versao,
            "icone": m.icone,
            "cor": m.cor,
            "ativo": m.ativo,
            "secoes": len((m.schema or {}).get("secoes", [])),
        }
        for m in modelos
    ]


def obter_modelo(db: Session, modelo_id: int) -> Optional[dict]:
    """Obtém um modelo específico."""
    m = db.query(ModeloVistoria).get(modelo_id)
    if not m:
        return None
    return {
        "id": m.id,
        "area": m.area,
        "nome": m.nome,
        "descricao": m.descricao,
        "versao": m.versao,
        "icone": m.icone,
        "cor": m.cor,
        "ativo": m.ativo,
        "schema": m.schema or {"secoes": []},
    }


def criar_modelo(db: Session, data: Dict[str, Any]) -> dict:
    """Cria novo modelo de vistoria."""
    m = ModeloVistoria(
        area=data.get("area", "engenharia"),
        nome=data["nome"],
        descricao=data.get("descricao"),
        schema=data.get("schema", {"secoes": []}),
        icone=data.get("icone", "📋"),
        cor=data.get("cor", "#2563eb"),
        ativo=data.get("ativo", True),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "nome": m.nome, "versao": m.versao}


def atualizar_modelo(db: Session, modelo_id: int, data: Dict[str, Any]) -> dict:
    """Atualiza um modelo de vistoria."""
    m = db.query(ModeloVistoria).get(modelo_id)
    if not m:
        return None
    for campo in ("area", "nome", "descricao", "icone", "cor", "ativo"):
        if campo in data:
            setattr(m, campo, data[campo])
    if "schema" in data:
        m.schema = data["schema"]
        m.versao = (m.versao or 1) + 1  # editar schema gera nova versão
    db.commit()
    return {"id": m.id, "nome": m.nome, "versao": m.versao}


# ============================================================================
# Vistorias
# ============================================================================


def listar_vistorias(
    db: Session, processo_id: Optional[int] = None, status: Optional[str] = None
) -> List[dict]:
    """Lista vistorias com filtros opcionais."""
    q = db.query(Vistoria)
    if processo_id:
        q = q.filter(Vistoria.processo_id == processo_id)
    if status:
        q = q.filter(Vistoria.status == status)
    vistorias = q.order_by(Vistoria.id.desc()).limit(200).all()
    return [_vistoria_dict(v) for v in vistorias]


def obter_vistoria(db: Session, vistoria_id: int) -> Optional[dict]:
    """Obtém vistoria com detalhes completos."""
    v = db.query(Vistoria).get(vistoria_id)
    if not v:
        return None
    d = _vistoria_dict(v)
    d["fotos_lista"] = [
        {
            "id": f.id,
            "campo_key": f.campo_key,
            "obrigatoria": f.obrigatoria,
            "legenda": f.legenda,
            "arquivo_path": f.arquivo_path,
        }
        for f in v.fotos
    ]
    d["assinaturas_lista"] = [
        {"id": a.id, "nome": a.nome, "documento": a.documento, "papel": a.papel}
        for a in v.assinaturas
    ]
    return d


def upsert_vistoria(
    db: Session, user: User, data: Dict[str, Any]
) -> Optional[dict]:
    """Cria ou atualiza vistoria (por uuid_offline para sync offline)."""
    modelo = db.query(ModeloVistoria).get(data.get("modelo_id"))
    if not modelo:
        return None

    v = None
    if data.get("uuid_offline"):
        v = db.query(Vistoria).filter(
            Vistoria.uuid_offline == data["uuid_offline"]
        ).first()

    if v is None:
        v = Vistoria(
            modelo_id=modelo.id,
            modelo_versao=modelo.versao,
            engenheiro_id=user.id,
            uuid_offline=data.get("uuid_offline"),
            criado_offline_em=data.get("criado_offline_em"),
        )
        db.add(v)

    for campo in ("processo_id", "local", "gps", "dados"):
        if campo in data:
            setattr(v, campo, data[campo])
    if data.get("status"):
        v.status = data["status"]
    v.sincronizado_em = datetime.utcnow().isoformat()

    db.commit()
    db.refresh(v)
    return _vistoria_dict(v)


def enviar_vistoria(
    db: Session, vistoria_id: int, processo_id: Optional[int] = None
) -> Optional[dict]:
    """Finaliza vistoria: marca enviada, vincula processo, gera PDF e laudo."""
    v = db.query(Vistoria).get(vistoria_id)
    if not v:
        return None
    if processo_id:
        if not db.query(Processo).get(processo_id):
            return None
        v.processo_id = processo_id
    v.status = "enviada"

    # Gerar PDF e laudo automático (Fase 2)
    try:
        laudo_txt = gerar_laudo_vistoria(v)
        v.laudo_rascunho = laudo_txt
        pdf_bytes = gerar_pdf_vistoria(v)
        if pdf_bytes:
            temp_pdf = (
                Path(tempfile.gettempdir())
                / f"vistoria_{v.id}_{datetime.utcnow().timestamp()}.pdf"
            )
            temp_pdf.write_bytes(pdf_bytes)
            v.pdf_path = str(temp_pdf)
    except Exception as e:
        print(f"Erro ao gerar PDF/laudo da vistoria {v.id}: {e}")

    db.commit()
    return {
        "id": v.id,
        "status": v.status,
        "processo_id": v.processo_id,
        "pdf_gerado": bool(v.pdf_path),
    }


def gerar_laudo(db: Session, vistoria_id: int) -> Optional[dict]:
    """Gera parecer técnico com Qwen."""
    v = db.query(Vistoria).get(vistoria_id)
    if not v:
        return None
    try:
        laudo = gerar_laudo_vistoria(v)
        v.laudo_rascunho = laudo
        db.commit()
        return {
            "id": v.id,
            "laudo": laudo[:500] + "..." if len(laudo) > 500 else laudo,
            "completo": laudo,
            "status": "gerado",
        }
    except Exception:
        return None


def obter_laudo(db: Session, vistoria_id: int) -> Optional[dict]:
    """Retorna laudo rascunho da vistoria."""
    v = db.query(Vistoria).get(vistoria_id)
    if not v:
        return None
    return {
        "id": v.id,
        "laudo_rascunho": v.laudo_rascunho or "Laudo não gerado ainda",
        "resumo": resumo_rpido_vistoria(v),
    }


def obter_ou_gerar_pdf(db: Session, vistoria_id: int) -> Optional[str]:
    """Obtém caminho PDF ou gera se não existir."""
    v = db.query(Vistoria).get(vistoria_id)
    if not v:
        return None

    # Se não tiver PDF gerado, gera na hora
    if not v.pdf_path or not Path(v.pdf_path).exists():
        try:
            pdf_bytes = gerar_pdf_vistoria(v)
            temp_pdf = (
                Path(tempfile.gettempdir())
                / f"vistoria_{v.id}_{datetime.utcnow().timestamp()}.pdf"
            )
            temp_pdf.write_bytes(pdf_bytes)
            v.pdf_path = str(temp_pdf)
            db.commit()
        except Exception:
            return None

    if not Path(v.pdf_path).exists():
        return None
    return v.pdf_path


def registrar_assinatura(
    db: Session, vistoria_id: int, data: Dict[str, Any]
) -> Optional[dict]:
    """Registra assinatura digital no PDF."""
    v = db.query(Vistoria).get(vistoria_id)
    if not v:
        return None

    if not v.pdf_path or not Path(v.pdf_path).exists():
        return None

    # Armazenar metadados de assinatura
    assinatura_meta = {
        "hash": data.get("hash_assinatura"),
        "certificado": data.get("certificado_cn"),
        "data_assinatura": data.get("data_assinatura", datetime.utcnow().isoformat()),
        "url_ts": data.get("timestamp_server_url"),
    }

    v.status = "assinada"
    v.dados = v.dados or {}
    v.dados["_assinatura_digital"] = assinatura_meta

    db.commit()
    return {
        "id": v.id,
        "status": v.status,
        "assinado_em": assinatura_meta.get("data_assinatura"),
        "certificado": assinatura_meta.get("certificado"),
    }


def adicionar_foto(
    db: Session, vistoria_id: int, data: Dict[str, Any]
) -> Optional[dict]:
    """Adiciona foto à vistoria."""
    import base64
    import hashlib

    v = db.query(Vistoria).get(vistoria_id)
    if not v:
        return None

    try:
        base64_data = data.get("base64_data", "")
        campo_key = data.get("campo_key")
        legenda = data.get("legenda", "")
        ordem = data.get("ordem", len(v.fotos))

        if not base64_data:
            return None

        # Salvar foto em arquivo temporário
        hash_foto = hashlib.md5(base64_data.encode()).hexdigest()[:12]
        temp_foto_path = (
            Path(tempfile.gettempdir()) / f"vistoria_{v.id}_foto_{hash_foto}.jpg"
        )

        # Decodificar e salvar
        if base64_data.startswith("data:image"):
            _, base64_data = base64_data.split(",", 1)

        foto_bytes = base64.b64decode(base64_data)
        temp_foto_path.write_bytes(foto_bytes)

        # Registrar no BD
        foto = VistoriaFoto(
            vistoria_id=v.id,
            campo_key=campo_key,
            legenda=legenda,
            arquivo_path=str(temp_foto_path),
            ordem=ordem,
        )
        db.add(foto)
        db.commit()
        db.refresh(foto)

        return {
            "id": foto.id,
            "vistoria_id": v.id,
            "arquivo_path": str(temp_foto_path),
            "legenda": legenda,
        }
    except Exception:
        return None
