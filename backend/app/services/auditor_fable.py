import logging
import json
import os
from sqlalchemy.orm import Session
from app.models import Laudo, LaudoVersao, AuditoriaFable

logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("SDK Anthropic não instalado. Instale com: pip install anthropic")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

PROMPT_FABLE = """ROLE: Você é auditor forense especializado em PERÍCIAS JUDICIAIS brasileiras.

TAREFA: Validar integridade técnica do rascunho de laudo contra normas técnicas, fontes e legislação.

CHECKLIST OBRIGATÓRIO:

### A. VALIDAÇÃO DE CITAÇÕES (CRÍTICO)
Para CADA lei, artigo ou norma citada:
- [ ] Existe? (ex: "Art. 406 CC" — SIM. "Art. 1.500 CPC" — NÃO)
- [ ] Redação condiz? (compare com norma fornecida)
- Marca como [✅ VÁLIDA], [⚠️ VERIFICAR], ou [❌ NÃO LOCALIZADA]

### B. ESTRUTURA ABNT (CRÍTICO)
- [ ] Tem IDENTIFICAÇÃO completa?
- [ ] Tem SÍNTESE DO OBJETO?
- [ ] Metodologia explícita com normas?
- [ ] RELATO DAS DILIGÊNCIAS com datas?
- [ ] ANÁLISE TÉCNICA?
- [ ] RESPOSTAS aos QUESITOS?
- [ ] CONCLUSÃO?
- [ ] ENCERRAMENTO com data/assinatura?

### C. INCONSISTÊNCIAS DE VALORES (CRÍTICO)
- [ ] Valores em ANÁLISE == valores em CONCLUSÃO?
- [ ] Memória de cálculo bate?

### D. RASTREABILIDADE (CRÍTICO)
- [ ] CADA conclusão tem evidência? (cite fls. XXX ou documento?)
- [ ] Não há afirmação "solto"?

### E. SINAIS DE ALERTA (Avisos)
- [ ] Termos subjetivos? ("é provável", "parece", "eu acho", "talvez")
- [ ] Fórmulas sem explicação?
- [ ] Lacunas de análise?

SAÍDA: Relatório JSON estruturado:
```json
{
  "validacoes_ok": ["✅ Identificação completa", ...],
  "avisos": ["⚠️ Fórmula não explicitada", ...],
  "erros_criticos": ["❌ Quesito não respondido", ...],
  "score": 0.82,
  "recomendacao": "Revisar erros críticos antes de emitir"
}
```

IMPORTANTE: Jamais reescreva o laudo. Apenas verifique. Bloqueia emissão se score < 0.6."""


def auditar_laudo(laudo_id: int, versao_numero: int, db: Session) -> AuditoriaFable:
    """Audita rascunho com Fable 5. Retorna AuditoriaFable ou levanta exceção."""
    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError("SDK Anthropic não instalado")

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    laudo = db.query(Laudo).filter(Laudo.id == laudo_id).first()
    if not laudo:
        raise ValueError(f"Laudo {laudo_id} não encontrado")

    versao = db.query(LaudoVersao).filter(
        LaudoVersao.laudo_id == laudo_id,
        LaudoVersao.numero_versao == versao_numero
    ).first()

    if not versao:
        raise ValueError(f"Versão {versao_numero} do laudo {laudo_id} não encontrada")

    rascunho = versao.conteudo_markdown
    processo = laudo.processo

    pdf_texto = ""
    if hasattr(processo, "arquivos") and processo.arquivos:
        try:
            for arquivo in processo.arquivos:
                if hasattr(arquivo, "conteudo"):
                    pdf_texto += f"\n{arquivo.conteudo[:1000]}"
        except Exception as e:
            logger.warning(f"Não conseguiu extrair PDFs para auditoria: {e}")

    prompt = f"""{PROMPT_FABLE}

RASCUNHO PARA AUDITAR:
{rascunho}

PDF DO PROCESSO (primeiras páginas):
{pdf_texto[:3000] if pdf_texto else "[Documentos não fornecidos]"}

NORMA TÉCNICA (referência):
NBC TP 01 R2 (Perícia Contábil) / NBR 13752:2024 (Perícia Engenharia)
"""

    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        texto_resposta = response.content[0].text

        relatorio_json = _parsear_json_fable(texto_resposta)

        auditoria = AuditoriaFable(
            laudo_id=laudo_id,
            versao_numero=versao_numero,
            relatorio_json=relatorio_json
        )
        db.add(auditoria)
        db.commit()
        db.refresh(auditoria)

        logger.info(f"Auditoria completa para laudo {laudo_id} v{versao_numero}, score={relatorio_json.get('score', 0)}")
        return auditoria

    except Exception as e:
        logger.error(f"Erro ao auditar laudo {laudo_id}: {e}")
        fallback_relatorio = {
            "validacoes_ok": [],
            "avisos": [f"⚠️ Erro ao chamar Fable 5: {str(e)}"],
            "erros_criticos": ["❌ Auditoria falhou — tente novamente"],
            "score": 0.0,
            "recomendacao": "Não emita sem auditoria bem-sucedida"
        }
        auditoria = AuditoriaFable(
            laudo_id=laudo_id,
            versao_numero=versao_numero,
            relatorio_json=fallback_relatorio
        )
        db.add(auditoria)
        db.commit()
        db.refresh(auditoria)
        return auditoria


def _parsear_json_fable(texto: str) -> dict:
    """Extrai JSON do texto de resposta do Fable."""
    import re

    match = re.search(r"```json\n(.*?)\n```", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("JSON inválido na resposta Fable, usando fallback")

    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning("Não conseguiu parsear JSON de Fable, retornando fallback")
    return {
        "validacoes_ok": [],
        "avisos": ["⚠️ Resposta Fable não continha JSON parseável"],
        "erros_criticos": [],
        "score": 0.5,
        "recomendacao": "Revisar resposta manualmente"
    }
