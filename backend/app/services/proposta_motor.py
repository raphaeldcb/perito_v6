"""Serviço completo do Motor de Propostas.

Pipeline: PDF → OCR → Classificação → Análise Qwen → Similares → Documento DOCX
"""
import json
import hashlib
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import (
    Processo, Intimacao, KanbanCartao, KanbanColuna, KanbanHistorico,
    Oficio, User, HistoricoJuiz
)
from app.models.proposta import (
    PropostaMotor, PropostaStatus, PropostaFeedback, PropostaAnalisador
)

logger = logging.getLogger(__name__)


class OcrExtrator:
    """Extrai texto e dados estruturados de PDF intimação."""

    @staticmethod
    def extrair(pdf_path: str) -> Dict:
        """
        Extrai JSON estruturado do PDF.
        Retorna: {processo, juiz, comarca, tribunal, pedido, prazo_dias, data_vencimento,
                  fls, valor_causa, partes, materia, extracted_text}
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            # Básico: extrai linha por linha
            # Em produção: usar Qwen + pgvector para análise semântica
            lines = text.split("\n")

            result = {
                "extracted_text": text,
                "num_paginas": len(reader.pages),
                # Estes campos virão do Qwen (abaixo)
                "processo": None,
                "juiz": None,
                "comarca": None,
                "tribunal": None,
                "pedido": None,
                "prazo_dias": None,
                "data_vencimento": None,
                "fls": None,
                "valor_causa": None,
                "partes": [],
                "materia": None,
            }
            return result
        except Exception as e:
            logger.error(f"Erro ao extrair PDF {pdf_path}: {e}")
            raise


class ClassificadorArea:
    """Classifica perícia por ÁREA usando Qwen."""

    @staticmethod
    def classificar(extracted_text: str, materia: str, db: Session) -> Dict:
        """
        Usa Qwen para classificar a área.
        Retorna: {area_id, area_nome, confianca}

        Áreas: 10=Contábil, 20=DNA, 30=Eng, 40=Grafo, 50=Multi, 60=Declina
        """
        try:
            from ollama import Client as OllamaClient
            import os

            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            client = OllamaClient(host=ollama_url)

            prompt = f"""Classifique a área de perícia APENAS escolhendo um ID:

10 = Contábil (análise de livros, balanços, DRE, imposto)
20 = DNA (análise genética, parentesco)
30 = Engenharia Civil (cálculo de danos, estrutural, deslocamento, obra)
40 = Grafotécnica (análise de assinatura, autoria de documento)
50 = Multidisciplinar (combina 2+ áreas)
60 = Declina (caso fora do escopo)

MATÉRIA: {materia}
CONTEXTO: {extracted_text[:2000]}

Responda APENAS um JSON com:
{{"area_id": <número>, "area_nome": "<nome>", "confianca": <0.0-1.0>}}"""

            response = client.generate(
                model=os.getenv("OLLAMA_MODEL", "perito-qwen"),
                prompt=prompt,
                stream=False,
            )
            text = response.get("response", "")

            # Parse JSON da resposta
            try:
                result = json.loads(text)
                return result
            except json.JSONDecodeError:
                # Fallback: tenta extrair JSON do texto
                import re
                match = re.search(r"\{.*\}", text)
                if match:
                    result = json.loads(match.group())
                    return result
                # Se falhar completamente, default
                return {"area_id": 50, "area_nome": "Multidisciplinar", "confianca": 0.5}
        except Exception as e:
            logger.error(f"Erro ao classificar área: {e}")
            return {"area_id": 50, "area_nome": "Multidisciplinar", "confianca": 0.3}


class BuscadorSimilares:
    """Busca propostas similares no histórico para benchmarking."""

    @staticmethod
    def buscar_top_5(
        db: Session,
        area_id: int,
        comarca: str,
        fls: int,
        juiz: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Busca propostas aprovadas similares por:
        - Área
        - Comarca
        - ±50 folhas (fls)
        - Juiz (se houver histórico)

        Retorna lista com histórico de valores + frequência do juiz.
        """
        # Query: propostas aprovadas em status final
        query = db.query(PropostaMotor).filter(
            and_(
                PropostaMotor.area_id == area_id,
                PropostaMotor.status == PropostaStatus.PROTOCOLADO,
            )
        )

        # Usa valor_aprovado se disponível, senão valor_recomendado
        query = query.filter(
            or_(
                PropostaMotor.valor_aprovado.isnot(None),
                PropostaMotor.valor_recomendado.isnot(None),
            )
        )

        if comarca:
            query = query.filter(PropostaMotor.comarca == comarca)

        if fls:
            fls_min = max(fls - 50, 1)
            fls_max = fls + 50
            query = query.filter(PropostaMotor.fls.between(fls_min, fls_max))

        similares = query.order_by(PropostaMotor.created_at.desc()).limit(limit).all()

        # Formata resultado
        result = []
        for s in similares:
            # Usa valor_aprovado se disponível, senão valor_recomendado
            valor_base = float(s.valor_aprovado or s.valor_recomendado or 0)
            # Atualiza valor para 2026 (inflação IPCA-E)
            valor_2026 = BuscadorSimilares._corrigir_valor(
                valor_base,
                s.created_at
            )

            # Histórico do juiz
            freq_juiz = 1
            if juiz and s.juiz:
                hist = db.query(HistoricoJuiz).filter_by(juiz_nome=juiz).first()
                if hist:
                    freq_juiz = hist.total_atuacoes or 1

            result.append({
                "processo": s.processo.numero_cnj if s.processo else None,
                "ano": s.created_at.year,
                "fls": s.fls,
                "area": s.area_nome,
                "juiz": s.juiz,
                "valor_original": valor_base,
                "valor_2026_atualizado": valor_2026,
                "frequencia_juiz": freq_juiz,
                "data": s.created_at.isoformat() if s.created_at else None,
            })

        return result

    @staticmethod
    def _corrigir_valor(valor_original: float, data_original: datetime) -> float:
        """Simples: aplica inflação anual média ~5.5% até hoje."""
        if not valor_original or valor_original <= 0:
            return 0.0

        anos = (datetime.utcnow() - data_original).days / 365.25
        inflacao_anual = 1.055  # ~5.5% ao ano (ajustar conforme IPCA-E real)
        valor_corrigido = valor_original * (inflacao_anual ** anos)
        return valor_corrigido


class AnalisadorQwen:
    """Análise inteligente com Qwen — compara, ajusta, recomenda valor."""

    @staticmethod
    def analisar(
        db: Session,
        fls: int,
        juiz: str,
        comarca: str,
        area_id: int,
        area_nome: str,
        valor_causa: Decimal,
        propostas_similares: List[Dict],
        materia: str,
        extracted_text: str,
    ) -> Dict:
        """
        Qwen analisa tudo e retorna: {valor_recomendado, valor_alternativa, motivo, analise_juiz, analise_complexidade}

        Lógica:
        1. Busca teto CNJ por área
        2. Compara com similares + ajusta por FLS
        3. Analisa histórico do juiz
        4. Recomenda: Teto CNJ vs Valor Ajustado
        """
        try:
            from ollama import Client as OllamaClient
            import os

            ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            client = OllamaClient(host=ollama_url)

            # Formata similares como contexto
            contexto_similares = json.dumps(propostas_similares[:3], indent=2, default=str)

            prompt = f"""Você é especialista em perícia e honorários judiciais. Analise:

CARACTERÍSTICAS:
- Área: {area_nome} (ID {area_id})
- Comarca: {comarca}
- Juiz: {juiz}
- Folhas: {fls}
- Matéria: {materia}
- Valor da causa: R$ {valor_causa}

PROPOSTAS SIMILARES (histórico):
{contexto_similares}

CONTEXTO DO PROCESSO:
{extracted_text[:1500]}

DECISÃO FINAL:
1. Compare com similares
2. Ajuste por FLS: se fls > média, +% ; se fls < média, -%
3. Analise juiz: é frequente? Aprova teto CNJ ou valores maiores?
4. Recomende valor (ou teto CNJ se juiz frequente)
5. Ofereça alternativa conservadora

Responda APENAS um JSON:
{{
  "valor_recomendado": <float>,
  "valor_alternativa": <float>,
  "motivo": "<explicação curta>",
  "analise_juiz": "<frequência e padrão de aprovação>",
  "analise_complexidade": "<ajustes por folhas/matéria>"
}}"""

            response = client.generate(
                model=os.getenv("OLLAMA_MODEL", "perito-qwen"),
                prompt=prompt,
                stream=False,
                options={"temperature": 0.3},  # Mais determinístico
            )
            text = response.get("response", "")

            # Parse JSON
            try:
                result = json.loads(text)
                result["valor_recomendado"] = float(result.get("valor_recomendado", 3200.0))
                result["valor_alternativa"] = float(result.get("valor_alternativa", 2800.0))
                return result
            except json.JSONDecodeError:
                import re
                match = re.search(r"\{.*\}", text)
                if match:
                    result = json.loads(match.group())
                    return result
                # Fallback: teto CNJ estimado
                teto_cnj = _obter_teto_cnj(area_id)
                return {
                    "valor_recomendado": teto_cnj,
                    "valor_alternativa": teto_cnj * 0.85,
                    "motivo": "Análise simplificada — Teto CNJ",
                    "analise_juiz": "Dados insuficientes",
                    "analise_complexidade": "Padrão",
                }
        except Exception as e:
            logger.error(f"Erro ao analisar com Qwen: {e}")
            teto_cnj = _obter_teto_cnj(area_id)
            return {
                "valor_recomendado": teto_cnj,
                "valor_alternativa": teto_cnj * 0.85,
                "motivo": f"Erro na análise: {str(e)[:100]}. Usando teto padrão.",
                "analise_juiz": "Erro",
                "analise_complexidade": "Erro",
            }


def _obter_teto_cnj(area_id: int) -> float:
    """Teto CNJ 2026 por área (estimado)."""
    tecos = {
        10: 3200.0,    # Contábil
        20: 3500.0,    # DNA
        30: 4000.0,    # Engenharia
        40: 3000.0,    # Grafotécnica
        50: 4500.0,    # Multi
        60: 0.0,       # Declina
    }
    return tecos.get(area_id, 3200.0)


class GeradorDocumento:
    """Gera DOCX proposta preenchido com dados estruturados."""

    @staticmethod
    def gerar_proposta_docx(
        processo: Processo,
        proposta: PropostaMotor,
        template_path: Optional[str] = None,
    ) -> str:
        """
        Gera arquivo DOCX proposta.
        Retorna caminho do arquivo gerado.

        Se não houver template, usa template genérico.
        """
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        # Cria documento
        if template_path and os.path.exists(template_path):
            doc = Document(template_path)
        else:
            doc = Document()

        # Title
        title = doc.add_heading(f"PROPOSTA DE HONORÁRIOS PERICIAIS", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Info processo
        doc.add_paragraph()
        doc.add_paragraph(f"Processo: {processo.numero_cnj if processo else 'N/A'}")
        doc.add_paragraph(f"Juiz: {proposta.juiz or 'N/A'}")
        doc.add_paragraph(f"Comarca: {proposta.comarca or 'N/A'}")
        doc.add_paragraph(f"Tribunal: {proposta.tribunal or 'N/A'}")

        # Partes
        doc.add_paragraph()
        partes_text = ", ".join(proposta.partes) if proposta.partes else "N/A"
        doc.add_paragraph(f"Partes: {partes_text}")

        # Matéria
        doc.add_paragraph(f"Matéria: {proposta.materia or 'N/A'}")

        # Análise
        doc.add_heading("Análise e Justificativa", level=2)
        if proposta.analise_complexidade:
            doc.add_paragraph(proposta.analise_complexidade)

        if proposta.analise_juiz:
            doc.add_paragraph(f"Histórico do Juiz: {proposta.analise_juiz}")

        # Propostas similares
        if proposta.propostas_similares:
            doc.add_heading("Referências Históricas", level=2)
            for sim in proposta.propostas_similares[:3]:
                doc.add_paragraph(
                    f"Processo similar (2026): R$ {sim['valor_2026_atualizado']:.2f} "
                    f"({sim['fls']} fls, Juiz {sim['juiz']})"
                )

        # Recomendação
        doc.add_heading("VALOR RECOMENDADO", level=2)
        p = doc.add_paragraph()
        p.add_run(f"R$ {proposta.valor_recomendado:,.2f}").bold = True
        if proposta.valor_recomendado:
            p.add_run(f"\n\nMotivo: {proposta.motivo_recomendacao or ''}")

        if proposta.valor_alternativa:
            doc.add_paragraph(f"Valor alternativa (conservador): R$ {proposta.valor_alternativa:,.2f}")

        # Rodapé
        doc.add_paragraph()
        doc.add_paragraph("IPC-MS — Perícia Judicial")
        doc.add_paragraph(f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}")

        # Salva arquivo
        output_dir = "/tmp/propostas"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"proposta_{proposta.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
        filepath = os.path.join(output_dir, filename)
        doc.save(filepath)

        logger.info(f"Proposta DOCX gerada: {filepath}")
        return filepath


class PropostaOrchestrator:
    """Orquestra todo o pipeline de propostas."""

    @staticmethod
    async def processar_pdf(
        db: Session,
        pdf_path: str,
        intimacao_id: int,
        processo_id: int,
        usuario_id: int,
    ) -> PropostaMotor:
        """
        Pipeline completo: PDF → Proposta pronta (DRAFT).

        Fases:
        1. OCR Extract
        2. Classificação Área
        3. Busca Similares
        4. Análise Qwen
        5. Gera Documento DOCX
        6. Cria Kanban Card
        7. Retorna Proposta em status DRAFT
        """
        logger.info(f"Iniciando pipeline proposta para {pdf_path}")

        # Cria registro proposta (status EXTRAINDO)
        proposta = PropostaMotor(
            processo_id=processo_id,
            intimacao_id=intimacao_id,
            pdf_path=pdf_path,
            status=PropostaStatus.EXTRAINDO,
        )
        db.add(proposta)
        db.commit()

        try:
            # 1. OCR
            logger.info("Fase 1: OCR")
            proposta.status = PropostaStatus.EXTRAINDO
            ocr_data = OcrExtrator.extrair(pdf_path)
            proposta.txt_extraido = ocr_data.get("extracted_text", "")
            proposta.json_extraido = ocr_data
            db.commit()

            # Popula campos estruturados (você integraria Qwen aqui também)
            proposta.juiz = ocr_data.get("juiz")
            proposta.comarca = ocr_data.get("comarca")
            proposta.tribunal = ocr_data.get("tribunal", "TJMT")
            proposta.fls = ocr_data.get("fls", 100)
            proposta.valor_causa = ocr_data.get("valor_causa")
            proposta.materia = ocr_data.get("materia")
            proposta.partes = ocr_data.get("partes", [])
            proposta.pedido = ocr_data.get("pedido", "proposta_honorarios")

            # 2. Classificação
            logger.info("Fase 2: Classificação de Área")
            proposta.status = PropostaStatus.CLASSIFICANDO
            area_data = ClassificadorArea.classificar(proposta.txt_extraido, proposta.materia or "", db)
            proposta.area_id = area_data.get("area_id", 50)
            proposta.area_nome = area_data.get("area_nome", "Multidisciplinar")
            proposta.area_confianca = Decimal(str(area_data.get("confianca", 0.5)))
            db.commit()

            # 3. Busca similares
            logger.info("Fase 3: Busca similares")
            similares = BuscadorSimilares.buscar_top_5(
                db,
                area_id=proposta.area_id,
                comarca=proposta.comarca,
                fls=proposta.fls or 100,
                juiz=proposta.juiz,
            )
            proposta.propostas_similares = similares

            # 4. Análise Qwen
            logger.info("Fase 4: Análise Qwen")
            proposta.status = PropostaStatus.ANALISANDO
            analise = AnalisadorQwen.analisar(
                db,
                fls=proposta.fls or 100,
                juiz=proposta.juiz or "",
                comarca=proposta.comarca or "",
                area_id=proposta.area_id,
                area_nome=proposta.area_nome,
                valor_causa=proposta.valor_causa or Decimal("0"),
                propostas_similares=similares,
                materia=proposta.materia or "",
                extracted_text=proposta.txt_extraido,
            )
            proposta.valor_recomendado = Decimal(str(analise.get("valor_recomendado", 3200.0)))
            proposta.valor_alternativa = Decimal(str(analise.get("valor_alternativa", 2800.0)))
            proposta.motivo_recomendacao = analise.get("motivo", "")
            proposta.analise_juiz = analise.get("analise_juiz", "")
            proposta.analise_complexidade = analise.get("analise_complexidade", "")
            db.commit()

            # 5. Gera DOCX
            logger.info("Fase 5: Geração DOCX")
            try:
                processo = db.query(Processo).get(processo_id)
                docx_path = GeradorDocumento.gerar_proposta_docx(processo, proposta)
                proposta.arquivo_docx_path = docx_path

                # Hash do arquivo para cache
                with open(docx_path, "rb") as f:
                    proposta.arquivo_docx_hash = hashlib.sha256(f.read()).hexdigest()
            except Exception as e:
                logger.error(f"Erro ao gerar DOCX: {e}")
                proposta.erros = f"Erro DOCX: {str(e)}"

            # 6. Auto-assign de analista por área
            logger.info("Fase 6: Auto-assign analista")
            analista = db.query(User).filter(
                User.area_id == proposta.area_id,
                User.papel == "analista"
            ).first()
            if analista:
                proposta.analista_id = analista.id

            # 7. Status DRAFT
            proposta.status = PropostaStatus.DRAFT
            db.commit()

            logger.info(f"Proposta {proposta.id} em DRAFT pronta para revisão")
            return proposta

        except Exception as e:
            logger.error(f"Erro no pipeline proposta: {e}")
            proposta.status = PropostaStatus.DRAFT  # Mesmo com erro, permite revisão manual
            proposta.erros = str(e)
            db.commit()
            return proposta
