"""
Master orchestrator for end-to-end laudo generation.

Task 4: Extract → RAG → Generate → Fill DOCX

Pipeline:
1. Extract: Use LaudoExtrator to get complete process data
2. RAG: Use LaudoRAGHibrido to search patterns or accept manual input
3. Generate: Build prompt and call Qwen for markdown content
4. Fill DOCX: Use LaudoDocxSafe to replace placeholders while preserving formatting

Features:
- Flexible input (unlimited fields in dados_entrada)
- No truncation (complete document extraction)
- RAG + manual hybrid approach
- Safe DOCX formatting preservation
- Retry logic for Qwen calls
- Comprehensive logging

Returns DOCX bytes ready for download/storage.
"""
import logging
import os
import time
import json
import requests
from typing import Dict, Any, Optional
from pathlib import Path
from docx import Document
from io import BytesIO
from sqlalchemy.orm import Session

from app.models import Processo
from app.services.laudo_extrator import LaudoExtrator
from app.services.laudo_rag_hibrido import LaudoRAGHibrido
from app.services.laudo_docx_safe import LaudoDocxSafe
from app.config.settings import Settings

logger = logging.getLogger(__name__)

# Load settings
settings = Settings()
QWEN_URL = settings.ollama_url  # e.g., http://172.17.0.1:11435
QWEN_MODEL = settings.qwen_model  # e.g., perito-qwen, qwen-turbo
QWEN_API_KEY = settings.qwen_api_key


class LaudoGeneratorV2:
    """Master orchestrator for laudo generation pipeline."""

    def __init__(self):
        """Initialize dependencies."""
        self.extrator = LaudoExtrator()
        self.rag = LaudoRAGHibrido()
        self.docx_safe = LaudoDocxSafe()

    def gerar_laudo_completo(self, db: Session, dados_entrada: Dict[str, Any]) -> bytes:
        """
        End-to-end laudo generation pipeline.

        Args:
            db: Database session
            dados_entrada: Flexible input dictionary with keys:
                - processo_id (required): ID of the Processo
                - tipo_laudo (required): Type of laudo (e.g., "contabil", "insalubridade")
                - template_path (optional): Path to DOCX template
                - numero_laudo (optional): Number/ID for the laudo
                - perito_id (optional): ID of the perito
                - nome_perito (optional): Name of perito
                - quesitos (optional): List of questions to answer
                - And unlimited extra fields (dados_planilha, honorarios, etc.)

        Returns:
            bytes: DOCX file content ready for download/storage

        Raises:
            ValueError: If required fields missing or process not found
            Exception: If Qwen call fails after retries
        """
        try:
            logger.info(f"[Task 4] Step 1/4: Extracting process data (processo_id={dados_entrada.get('processo_id')})")

            # Step 1: Extract
            processo = self._carregar_processo(db, dados_entrada)
            dados_processo = self.extrator.extrair_processo(processo)
            logger.info(f"[Task 4] Step 1/4 ✓ Extracted {len(dados_processo['documentos'])} documents")

            logger.info("[Task 4] Step 2/4: RAG search or manual fallback")

            # Step 2: RAG
            perito_id = dados_entrada.get("perito_id", 1)  # Default to admin
            tipo_laudo = dados_entrada.get("tipo_laudo", "geral")
            contexto = self.rag.buscar_ou_aceitar_manual(
                db, tipo_laudo, perito_id, dados_entrada
            )
            logger.info(f"[Task 4] Step 2/4 ✓ RAG origem={contexto['origem']}")

            logger.info("[Task 4] Step 3/4: Generating markdown via Qwen")

            # Step 3: Generate
            prompt = self._montar_prompt(dados_entrada, dados_processo, contexto)
            markdown = self._chamar_qwen(prompt)
            logger.info(f"[Task 4] Step 3/4 ✓ Generated {len(markdown)} chars of markdown")

            logger.info("[Task 4] Step 4/4: Filling DOCX template")

            # Step 4: Fill DOCX
            docx_bytes = self._preencher_docx(
                dados_entrada, dados_processo, contexto, markdown
            )
            logger.info(f"[Task 4] Step 4/4 ✓ DOCX ready ({len(docx_bytes)} bytes)")

            logger.info("[Task 4] ✅ Pipeline complete - laudo ready for download")
            return docx_bytes

        except Exception as e:
            logger.error(f"[Task 4] ❌ Pipeline failed: {str(e)}", exc_info=True)
            raise

    def _carregar_processo(self, db: Session, dados_entrada: Dict[str, Any]) -> Processo:
        """Load Processo from database, validate it exists."""
        processo_id = dados_entrada.get("processo_id")
        if not processo_id:
            raise ValueError("dados_entrada must include 'processo_id'")

        processo = db.query(Processo).filter(Processo.id == processo_id).first()
        if not processo:
            raise ValueError(f"Processo {processo_id} not found in database")

        return processo

    def _montar_prompt(
        self,
        dados_entrada: Dict[str, Any],
        dados_processo: Dict[str, Any],
        contexto: Dict[str, Any],
    ) -> str:
        """
        Build Qwen prompt with complete context.

        Structure:
        1. Role + especialidade
        2. Context: tipo, número, partes, vara
        3. RAG patterns (if available)
        4. Complete documents (no truncation)
        5. Manual data
        6. Quesitos
        7. Task description

        Args:
            dados_entrada: Input data
            dados_processo: Extracted process data
            contexto: RAG + manual context

        Returns:
            Complete prompt string
        """
        tipo_laudo = dados_entrada.get("tipo_laudo", "geral")
        numero_laudo = dados_entrada.get("numero_laudo", "")
        numero_processo = dados_processo.get("metadata", {}).get("numero", "")
        partes = dados_processo.get("metadata", {}).get("partes", {})
        autor = partes.get("reqte", "Não informado")
        reu = partes.get("reqdo", "Não informado")
        vara = dados_processo.get("metadata", {}).get("vara", "Não informada")
        tipo_especialidade = dados_processo.get("metadata", {}).get("tipo", "")

        # Extract quesitos
        quesitos = dados_entrada.get("quesitos", [])
        if isinstance(quesitos, str):
            quesitos = [quesitos]
        quesitos_str = "\n".join([f"- {q}" for q in quesitos]) if quesitos else "Nenhum quesito especificado"

        # Extract complete text (NO TRUNCATION)
        texto_completo = dados_processo.get("texto_completo", "")

        # Extract RAG patterns (if available)
        padroes_rag = contexto.get("padroes_rag", {})
        secoes = padroes_rag.get("secoes", []) if padroes_rag else []
        termos_top = padroes_rag.get("termos_top_10", {}) if padroes_rag else {}
        estilo = padroes_rag.get("estilo", "") if padroes_rag else ""

        # Manual data
        dados_manuais = contexto.get("dados_manuais", {})
        dados_planilha = dados_manuais.get("dados_planilha", "")
        honorarios = dados_manuais.get("honorarios", "")
        observacoes = dados_manuais.get("observacoes", "")

        # Extra fields
        campos_extras = contexto.get("campos_extras", {})

        # Build prompt
        prompt = f"""ROLE: Você é perito judicial especializado em {tipo_laudo.lower()}.
Sua responsabilidade é elaborar um laudo técnico imparcial, fundamentado e completo.

CONTEXTO DO PROCESSO:
- Tipo de Laudo: {tipo_laudo}
- Número do Laudo: {numero_laudo}
- Número do Processo: {numero_processo}
- Vara/Tribunal: {vara}
- Especialidade: {tipo_especialidade}
- Autor: {autor}
- Réu: {reu}

QUESITOS A RESPONDER:
{quesitos_str}

PADRÕES DE LAUDOS ANTERIORES:
"""

        if estilo:
            prompt += f"- Estilo: {estilo}\n"

        if secoes:
            prompt += f"- Seções padrão: {', '.join(secoes[:5])}...\n"

        if termos_top:
            termos_str = ", ".join([f"{t} ({c})" for t, c in list(termos_top.items())[:5]])
            prompt += f"- Termos frequentes: {termos_str}\n"

        prompt += f"""
ORIGEM DOS DADOS: {contexto.get('origem', 'manual')}

DOCUMENTOS DO PROCESSO (COMPLETOS, SEM TRUNCAÇÃO):
{texto_completo}

"""

        if dados_planilha:
            prompt += f"DADOS DE PLANILHA (MANUAL):\n{dados_planilha}\n\n"

        if honorarios:
            prompt += f"HONORÁRIOS: {honorarios}\n\n"

        if observacoes:
            prompt += f"OBSERVAÇÕES ESPECIAIS:\n{observacoes}\n\n"

        if campos_extras:
            prompt += "DADOS ADICIONAIS:\n"
            for chave, valor in campos_extras.items():
                prompt += f"- {chave}: {valor}\n"
            prompt += "\n"

        prompt += """ESTRUTURA OBRIGATÓRIA DO LAUDO:

## 1. IDENTIFICAÇÃO
- Número do processo
- Vara/Juiz
- Partes e qualificação
- Perito e qualificação profissional

## 2. SÍNTESE DO OBJETO
- Resumo da lide
- Objetivo específico da perícia

## 3. METODOLOGIA
- Procedimentos utilizados
- Normas e referências técnicas aplicadas

## 4. RELATO DAS DILIGÊNCIAS
- Datas, locais, documentos analisados
- Limitações encontradas

## 5. ANÁLISE TÉCNICA
- Discussão detalhada
- Memória de cálculo (se aplicável)
- Fundamentação legal e técnica

## 6. RESPOSTAS AOS QUESITOS
- Resposta clara e numerada para CADA quesito
- Fundamentação objetiva com referência às fls.

## 7. CONCLUSÃO
- Parecer técnico final
- Síntese dos resultados

## 8. ENCERRAMENTO
- Local, data, assinatura

REQUISITOS CRÍTICOS:
1. Linguagem técnica clara, sem subjetividades
2. TODA conclusão com EVIDÊNCIA (cite fls. XXX dos autos)
3. Neutralidade absoluta
4. Se dados insuficientes, aponte a limitação
5. Nenhum artigo/lei/norma pode ser invenção (alucinação = zero valor)
6. Valores em conclusão devem bater com valores em análise (consistência)
7. Respostas aos quesitos são OBRIGATÓRIAS e NUMERADAS

FORMATO: Markdown estruturado com títulos ##, listas, tabelas quando necessário.
SAÍDA: Rascunho de Laudo em Markdown pronto para revisão e assinatura.

Elabore o laudo agora:"""

        return prompt

    def _chamar_qwen(self, prompt: str, max_retries: int = 3) -> str:
        """
        Call Qwen API (Ollama or external) with retry logic.

        Args:
            prompt: Complete prompt for Qwen
            max_retries: Maximum retry attempts

        Returns:
            Generated markdown response

        Raises:
            Exception: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"[Qwen] Attempt {attempt + 1}/{max_retries}")

                # Determine endpoint based on QWEN_URL format
                if "ollama" in QWEN_URL.lower() or "11434" in QWEN_URL or "11435" in QWEN_URL:
                    # Local Ollama
                    endpoint = f"{QWEN_URL}/api/generate"
                    payload = {
                        "model": QWEN_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.2,
                        "top_p": 0.9,
                        "top_k": 40,
                    }
                else:
                    # External API (e.g., DashScope)
                    endpoint = f"{QWEN_URL}/api/v1/chat/completions"
                    payload = {
                        "model": QWEN_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    }
                    if QWEN_API_KEY:
                        payload["api_key"] = QWEN_API_KEY

                response = requests.post(
                    endpoint,
                    json=payload,
                    timeout=300,  # 5 minute timeout
                    headers={"Authorization": f"Bearer {QWEN_API_KEY}"} if QWEN_API_KEY and "ollama" not in QWEN_URL.lower() else {}
                )

                if response.status_code == 200:
                    result = response.json()

                    # Extract response based on format
                    if "response" in result:
                        # Ollama format
                        return result["response"]
                    elif "choices" in result:
                        # OpenAI-like format
                        return result["choices"][0]["message"]["content"]
                    else:
                        logger.warning(f"Unexpected response format: {result.keys()}")
                        raise ValueError("Unexpected Qwen response format")

                else:
                    logger.warning(f"Qwen HTTP {response.status_code}: {response.text[:200]}")

                    if response.status_code >= 500 and attempt < max_retries - 1:
                        # Server error, retry
                        wait_time = (attempt + 1) * 5
                        logger.info(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                    raise Exception(f"Qwen error: {response.text}")

            except requests.exceptions.Timeout:
                logger.warning(f"Qwen timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 5)
                    continue
                raise

            except Exception as e:
                logger.error(f"Qwen error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 5)
                    continue
                raise

        raise Exception(f"Qwen failed after {max_retries} attempts")

    def _preencher_docx(
        self,
        dados_entrada: Dict[str, Any],
        dados_processo: Dict[str, Any],
        contexto: Dict[str, Any],
        markdown: str,
    ) -> bytes:
        """
        Fill DOCX template with all data, preserving formatting.

        Uses LaudoDocxSafe for safe placeholder replacement.

        Args:
            dados_entrada: Original input
            dados_processo: Extracted process data
            contexto: RAG + manual context
            markdown: Generated content from Qwen

        Returns:
            DOCX bytes
        """
        # Load template
        template_path = dados_entrada.get("template_path")

        if not template_path:
            # Use minimal default template
            doc = self._criar_template_padrao()
        else:
            template_path = Path(template_path)
            if not template_path.exists():
                logger.warning(f"Template not found: {template_path}, using default")
                doc = self._criar_template_padrao()
            else:
                doc = Document(str(template_path))

        # Prepare replacements from all sources
        replacements = self._preparar_replacements(
            dados_entrada, dados_processo, contexto, markdown
        )

        # Use LaudoDocxSafe to replace placeholders
        self.docx_safe.replace_in_document(doc, replacements)

        # Save to bytes
        output = BytesIO()
        doc.save(output)
        output.seek(0)
        return output.getvalue()

    def _preparar_replacements(
        self,
        dados_entrada: Dict[str, Any],
        dados_processo: Dict[str, Any],
        contexto: Dict[str, Any],
        markdown: str,
    ) -> Dict[str, str]:
        """
        Build dictionary of placeholder → replacement value.

        Sources:
        1. Direct from dados_entrada (all fields, including tipo_laudo)
        2. From dados_processo metadata
        3. From contexto (manual + RAG)

        Args:
            dados_entrada: Input data
            dados_processo: Extracted data
            contexto: RAG + manual
            markdown: Generated content

        Returns:
            Dict of replacements
        """
        replacements = {}

        # From input (ALL fields including tipo_laudo)
        for key, value in dados_entrada.items():
            if key not in ("processo_id", "template_path"):
                placeholder = f"{{{{{key}}}}}"
                replacements[placeholder] = str(value)

        # From process metadata
        metadata = dados_processo.get("metadata", {})
        partes = metadata.get("partes", {})

        if partes.get("reqte"):
            replacements["{{nome_autor}}"] = partes["reqte"]
            replacements["{{autor}}"] = partes["reqte"]

        if partes.get("reqdo"):
            replacements["{{nome_reu}}"] = partes["reqdo"]
            replacements["{{reu}}"] = partes["reqdo"]

        if metadata.get("numero"):
            replacements["{{numero_processo}}"] = metadata["numero"]

        if metadata.get("vara"):
            replacements["{{vara}}"] = metadata["vara"]

        # From generated markdown
        replacements["{{conteudo_laudo}}"] = markdown

        # From manual data
        dados_manuais = contexto.get("dados_manuais", {})
        for key, value in dados_manuais.items():
            placeholder = f"{{{{{key}}}}}"
            replacements[placeholder] = str(value)

        return replacements

    def _criar_template_padrao(self) -> Document:
        """Create a minimal default DOCX template if none provided."""
        doc = Document()

        doc.add_heading("Laudo Pericial", level=1)

        doc.add_heading("Identificação", level=2)
        doc.add_paragraph("Laudo número: {{numero_laudo}}")
        doc.add_paragraph("Processo: {{numero_processo}}")
        doc.add_paragraph("Vara: {{vara}}")
        doc.add_paragraph("Tipo: {{tipo_laudo}}")

        doc.add_heading("Partes", level=2)
        table = doc.add_table(rows=3, cols=2)
        table.rows[0].cells[0].text = "Autor"
        table.rows[0].cells[1].text = "{{nome_autor}}"
        table.rows[1].cells[0].text = "Réu"
        table.rows[1].cells[1].text = "{{nome_reu}}"
        table.rows[2].cells[0].text = "Perito"
        table.rows[2].cells[1].text = "{{nome_perito}}"

        doc.add_heading("Conteúdo do Laudo", level=2)
        doc.add_paragraph("{{conteudo_laudo}}")

        return doc
