"""Registro central dos tipos de Job que a fila (app/routes/jobs.py +
mac_agent/scripts/mac_agent.py) sabe processar.

Fonte única de verdade para o endpoint GET /api/v1/workflows/nodes/types
(introspecção de nós disponíveis no canvas visual). Cada entrada documenta
os campos de `payload` esperados (inputs) e os campos de `resultado`
produzidos (outputs) — extraídos direto do que `_aplicar_resultado()` em
app/routes/jobs.py de fato lê/escreve, não é papel.

`integrado=True`  -> tem efeito colateral automático quando o job conclui
                      (grava em Laudo/Oficio/Intimacao/etc via
                      `_aplicar_resultado`), então encadear no workflow
                      builder funciona de ponta a ponta hoje.
`integrado=False` -> a fila processa e guarda `job.resultado`, mas nenhuma
                      tabela de negócio é atualizada automaticamente ainda;
                      ainda é útil como nó (ex: gerar um artefato bruto),
                      mas não dispare como se fosse "concluído no sistema".
"""
from typing import Any, Dict, List, TypedDict


class JobTypeInfo(TypedDict):
    tipo: str
    label: str
    description: str
    expected_inputs: List[str]
    expected_outputs: List[str]
    integrado: bool


JOB_TYPE_REGISTRY: List[JobTypeInfo] = [
    {
        "tipo": "gerar_laudo",
        "label": "Gerar Laudo (Qwen)",
        "description": "mac_agent gera rascunho via Ollama local e materializa LaudoVersao + DOCX assinado",
        "expected_inputs": ["laudo_id"],
        "expected_outputs": ["markdown"],
        "integrado": True,
    },
    {
        "tipo": "protocolo_laudo",
        "label": "Protocolar Laudo",
        "description": "Protocola o DOCX do laudo no eSAJ via A3 (Windows/WebSigner)",
        "expected_inputs": ["laudo_id", "arquivo_path"],
        "expected_outputs": ["protocolo_numero"],
        "integrado": True,
    },
    {
        "tipo": "protocolo_oficio",
        "label": "Protocolar Ofício",
        "description": "Protocola um ofício (proposta/ratifica/declina) no eSAJ via A3",
        "expected_inputs": ["oficio_id"],
        "expected_outputs": ["protocolo_numero"],
        "integrado": True,
    },
    {
        "tipo": "protocolo",
        "label": "Protocolar (genérico)",
        "description": "Protocola um item de Kanban/fila de protocolo genérico no eSAJ",
        "expected_inputs": ["cartao_id", "item_protocolo_id"],
        "expected_outputs": ["protocolo_numero"],
        "integrado": True,
    },
    {
        "tipo": "esaj_intimacoes",
        "label": "Buscar Intimações (ESAJ)",
        "description": "Varre o ESAJ por novas intimações e cria Processo/Intimacao pendentes",
        "expected_inputs": [],
        "expected_outputs": ["intimacoes"],
        "integrado": True,
    },
    {
        "tipo": "esaj_sincronizar",
        "label": "Sincronizar Autos (ESAJ)",
        "description": "Baixa/atualiza os autos de um processo específico no ESAJ",
        "expected_inputs": ["numero_cnj"],
        "expected_outputs": ["pdf_path"],
        "integrado": True,
    },
    {
        "tipo": "esaj_download",
        "label": "Baixar Autos (ESAJ)",
        "description": "Baixa o PDF dos autos de um processo do ESAJ e cria Intimacao tipo 'autos'",
        "expected_inputs": ["processo_id", "tribunal"],
        "expected_outputs": ["pdf_path"],
        "integrado": True,
    },
    {
        "tipo": "analise_ia",
        "label": "Analisar Intimação (IA)",
        "description": "Extrai dados estruturados de uma intimação (Qwen) e propaga partes/vara/juiz pro processo",
        "expected_inputs": ["intimacao_id"],
        "expected_outputs": ["dados"],
        "integrado": True,
    },
    {
        "tipo": "analisar_captacao",
        "label": "Analisar Captação (DJEN)",
        "description": "Classifica oportunidades do diário oficial (área/mérito/advogado/score)",
        "expected_inputs": [],
        "expected_outputs": ["analises"],
        "integrado": True,
    },
    {
        "tipo": "rascunho_email_captacao",
        "label": "Rascunho de E-mail (Captação)",
        "description": "Gera rascunho de e-mail de captação para uma Oportunidade",
        "expected_inputs": ["oportunidade_id"],
        "expected_outputs": ["email"],
        "integrado": True,
    },
    {
        "tipo": "indexar_rag",
        "label": "Indexar no RAG",
        "description": "Gera embedding (pgvector) de um texto/laudo pra busca semântica",
        "expected_inputs": ["origem", "ref_id", "texto"],
        "expected_outputs": [],
        "integrado": False,
    },
    {
        "tipo": "converter_pdf",
        "label": "Converter PDF",
        "description": "OCR + extração de texto de um PDF (pipeline v5.0)",
        "expected_inputs": ["pdf_path"],
        "expected_outputs": ["texto"],
        "integrado": False,
    },
    {
        "tipo": "analise_midia",
        "label": "Analisar Mídia",
        "description": "Análise de vídeo/áudio/imagem (fake media detector)",
        "expected_inputs": ["arquivo_path"],
        "expected_outputs": ["resultado"],
        "integrado": False,
    },
    {
        "tipo": "interpretar_decisao",
        "label": "Interpretar Decisão Judicial",
        "description": "IA interpreta o teor de uma decisão/despacho",
        "expected_inputs": ["intimacao_id"],
        "expected_outputs": ["interpretacao"],
        "integrado": False,
    },
    {
        "tipo": "interpretar_decisao_oficial",
        "label": "Interpretar Decisão Oficial (Padrão Semântico)",
        "description": (
            "Lê o PDF oficial da decisão (processo.decisao_oficial_path), tokeniza a "
            "regra semântica do padrão de cálculo e pede ao Qwen as datas de cada "
            "marco processual — roda in-process via BackgroundTasks, não pelo "
            "agente Windows/Mac (ver app/jobs/interpretar_decisao_oficial.py)"
        ),
        "expected_inputs": ["padrao_id", "processo_id"],
        "expected_outputs": ["arvore_decisao_id", "datas_sugeridas"],
        "integrado": True,
    },
    {
        "tipo": "pje_download_autos",
        "label": "Baixar Autos (PJe)",
        "description": "Baixa autos de processo no PJe (TJMT) via agente Windows",
        "expected_inputs": ["numero_cnj", "tribunal"],
        "expected_outputs": ["pdf_path"],
        "integrado": False,
    },
    {
        "tipo": "projuris_sync",
        "label": "Sincronizar Projuris",
        "description": "Sincroniza dados de um processo com o Projuris",
        "expected_inputs": ["processo_id"],
        "expected_outputs": [],
        "integrado": False,
    },
    {
        "tipo": "sugerir_campos",
        "label": "Sugerir Campos (IA)",
        "description": "IA sugere preenchimento de campos do cadastro a partir de documento",
        "expected_inputs": ["pdf_path"],
        "expected_outputs": ["campos"],
        "integrado": False,
    },
    {
        "tipo": "gerar_documento",
        "label": "Gerar Documento",
        "description": "Gera documento (termo, recibo, etc.) a partir de template",
        "expected_inputs": ["template", "dados"],
        "expected_outputs": ["arquivo_path"],
        "integrado": False,
    },
    {
        "tipo": "analise_produtividade",
        "label": "Analisar Produtividade (AssistProduction/Qwen)",
        "description": (
            "Qwen local (Mac) dá parecer contextual sobre os apps 'suspeitos' "
            "de um device/dia (heurística já rodou na ingestão) — resultado "
            "fica em Job.resultado (classificacao + justificativa)"
        ),
        "expected_inputs": ["device_id", "data", "apps_suspeitos"],
        "expected_outputs": ["classificacao", "justificativa"],
        "integrado": True,
    },
]


JOB_TYPE_BY_TIPO: Dict[str, JobTypeInfo] = {j["tipo"]: j for j in JOB_TYPE_REGISTRY}


def is_valid_job_type(tipo: str) -> bool:
    return tipo in JOB_TYPE_BY_TIPO
