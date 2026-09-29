import logging
import json
import re
from sqlalchemy.orm import Session
from app.models import Laudo, LaudoVersao

logger = logging.getLogger(__name__)


def validar_antes_emitir(laudo_id: int, db: Session) -> dict:
    """Valida laudo antes de emitir. Retorna {erros_criticos, avisos, pode_emitir}."""
    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise ValueError(f"Laudo {laudo_id} não encontrado")

    versao = db.query(LaudoVersao).filter(
        LaudoVersao.laudo_id == laudo_id
    ).order_by(LaudoVersao.numero_versao.desc()).first()

    if not versao:
        return {
            "erros_criticos": ["Nenhuma versão do laudo encontrada"],
            "avisos": [],
            "pode_emitir": False
        }

    md = versao.conteudo_markdown
    erros_criticos = []
    avisos = []

    # 1. Seções obrigatórias
    secoes_obrigatorias = [
        "## 1. IDENTIFICAÇÃO",
        "## 2. SÍNTESE",
        "## 3. METODOLOGIA",
        "## 5. ANÁLISE TÉCNICA",
        "## 6. RESPOSTAS",
        "## 7. CONCLUSÃO"
    ]

    for secao in secoes_obrigatorias:
        if secao not in md:
            erros_criticos.append(f"Falta seção obrigatória: {secao}")

    # 2. Quesitos respondidos
    quesitos = []
    if laudo.quesitos:
        try:
            quesitos = json.loads(laudo.quesitos)
        except json.JSONDecodeError:
            quesitos = laudo.quesitos if isinstance(laudo.quesitos, list) else []

    for i, q in enumerate(quesitos, 1):
        if f"**Quesito {i}" not in md and f"Quesito {i}" not in md:
            erros_criticos.append(f"Quesito {i} não respondido")

    # 3. Valores consistentes
    valores_analise = re.findall(r"R\$\s+([\d.,]+)", md)
    partes = md.split("## 7. CONCLUSÃO")
    if len(partes) > 1:
        valores_conclusao = re.findall(r"R\$\s+([\d.,]+)", partes[1])
    else:
        valores_conclusao = []

    def normalizar(v):
        return float(v.replace(".", "").replace(",", "."))

    if valores_analise and valores_conclusao:
        try:
            va_last = normalizar(valores_analise[-1])
            vc_last = normalizar(valores_conclusao[-1])

            if abs(va_last - vc_last) > 1:
                avisos.append(
                    f"⚠️ Valores podem estar inconsistentes: análise={va_last:.2f}, conclusão={vc_last:.2f}"
                )
        except (ValueError, IndexError):
            avisos.append("⚠️ Não conseguiu validar consistência de valores (formato)")

    # 4. Termos subjetivos
    termos_ruins = ["parece", "eu acho", "provavelmente", "talvez", "pode ser"]
    for termo in termos_ruins:
        if termo.lower() in md.lower():
            avisos.append(f"⚠️ Uso de termo subjetivo: '{termo}'")

    # 5. Identificação do perito
    if "CRC" not in md and "CREA" not in md and "OAB" not in md:
        avisos.append("⚠️ Falta identificação clara do perito (CRC/CREA/OAB)")

    # 6. Comprimento mínimo
    if len(md) < 500:
        erros_criticos.append("Laudo muito curto (< 500 caracteres)")

    # 7. [ERRO] ou [ERROR] no conteúdo
    if "[ERRO" in md or "[ERROR" in md:
        erros_criticos.append("Laudo contém marcadores de erro ([ERRO] ou [ERROR])")

    return {
        "erros_criticos": erros_criticos,
        "avisos": avisos,
        "pode_emitir": len(erros_criticos) == 0
    }
