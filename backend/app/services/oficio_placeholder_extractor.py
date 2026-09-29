"""
Extração de placeholders de documentos DOCX e mapeamento automático com dados do processo.

SEGURANÇA:
- ReDoS Fix (P1): compiled regex pattern com validação
- Formula Injection Fix (P0): simpleeval ao invés de eval()
"""
import logging
import re
from datetime import date
from typing import List, Dict, Tuple
from io import BytesIO

logger = logging.getLogger(__name__)

# P1: Regex compilado com padrão restritivo (evita ReDoS)
# Apenas permite A-Z, números e underscore (não recursivo)
PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z_0-9]+)\}\}")


def extrair_placeholders_docx(docx_bytes: bytes) -> List[str]:
    """
    Lê um arquivo DOCX (como bytes) e extrai todos os placeholders {{CAMPO}}.

    P1: Usa regex compilado e restritivo (PLACEHOLDER_PATTERN) para evitar ReDoS.
    Padrão: {{[A-Z_0-9]+}} apenas — sem aninhamento ou quantificadores perigosos.

    Args:
        docx_bytes: Bytes do arquivo DOCX

    Returns:
        Lista de placeholders únicos encontrados, ex: ["{{NUMERO_PROCESSO}}", "{{DESLOCAMENTO}}"]

    Raises:
        ValueError: Se o DOCX está corrompido ou não pode ser lido
    """
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx não instalado. Execute: pip install python-docx")

    try:
        doc = Document(BytesIO(docx_bytes))
    except Exception as e:
        logger.error(f"Erro ao abrir DOCX: {e}")
        raise ValueError(f"DOCX corrompido ou inválido: {str(e)}")

    placeholders = set()

    # P1: Usa padrão compilado (evita ReDoS e melhora performance)
    # Busca em parágrafos
    for para in doc.paragraphs:
        matches = PLACEHOLDER_PATTERN.findall(para.text)
        for match in matches:
            placeholders.add(f"{{{{{match}}}}}")

    # Busca em tabelas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    matches = PLACEHOLDER_PATTERN.findall(para.text)
                    for match in matches:
                        placeholders.add(f"{{{{{match}}}}}")

    logger.info(f"Extraídos {len(placeholders)} placeholders únicos do DOCX")
    return sorted(list(placeholders))


def auto_mapear_campos(processo, placeholders: List[str]) -> Dict[str, Dict]:
    """
    Tenta mapear automaticamente placeholders com dados do processo.

    Args:
        processo: Objeto Processo da DB
        placeholders: Lista de placeholders, ex: ["{{NUMERO_PROCESSO}}", "{{DESLOCAMENTO}}"]

    Returns:
        Dict com estrutura:
        {
            "mapped": {
                "{{NUMERO_PROCESSO}}": {"value": "0001234-56.2022.8.12.0007", "source": "processo.numero_cnj"},
                ...
            },
            "unmapped": ["{{DESLOCAMENTO}}", "{{VALOR_DESLOCAMENTO}}"]
        }
    """
    hoje = date.today()
    data_ext = f"{hoje.day} de {_mes_extenso(hoje.month)} de {hoje.year}"

    # Mapa de placeholders → (valor, fonte)
    mapping_values = {
        "{{NUMERO_PROCESSO}}": (processo.numero_cnj, "processo.numero_cnj"),
        "{{CNJ}}": (processo.numero_cnj, "processo.numero_cnj"),
        "{{Nº}}": (processo.numero_cnj, "processo.numero_cnj"),
        "{{JUIZ}}": (processo.juiz, "processo.juiz"),
        "{{MAGISTRADO}}": (processo.juiz, "processo.juiz"),
        "{{VARA}}": (processo.vara, "processo.vara"),
        "{{COMARCA}}": (processo.tribunal or "Campo Grande", "processo.tribunal"),
        "{{AUTOR}}": (processo.autor, "processo.autor"),
        "{{REQUERENTE}}": (processo.autor, "processo.autor"),
        "{{REU}}": (processo.reu, "processo.reu"),
        "{{REQUERIDO}}": (processo.reu, "processo.reu"),
        "{{ESPECIALIDADE}}": (processo.especialidade, "processo.especialidade"),
        "{{AREA}}": (processo.especialidade, "processo.especialidade"),
        "{{HONORARIOS}}": (_valor_br(processo.honorarios), "processo.honorarios"),
        "{{VALOR}}": (_valor_br(processo.honorarios), "processo.honorarios"),
        "{{RESPONSAVEL}}": (getattr(processo, "responsavel", None), "processo.responsavel"),
        "{{DATA}}": (data_ext, "date.today"),
        "{{DATA_HOJE}}": (hoje.strftime("%d/%m/%Y"), "date.today"),
    }

    mapped = {}
    unmapped = []

    for placeholder in placeholders:
        if placeholder in mapping_values:
            value, source = mapping_values[placeholder]
            if value not in (None, ""):
                mapped[placeholder] = {"value": str(value), "source": source}
            else:
                unmapped.append(placeholder)
        else:
            unmapped.append(placeholder)

    logger.info(f"Mapeados {len(mapped)}/{len(placeholders)} placeholders. "
                f"Faltando: {len(unmapped)}")

    return {"mapped": mapped, "unmapped": unmapped}


def validar_mapeamento_manual(campo: str, valor_input: dict, processo=None) -> dict:
    """
    Valida e processa um mapeamento manual de campo.

    Args:
        campo: Nome do campo, ex "{{DESLOCAMENTO}}"
        valor_input: Dict com dados do mapeamento, ex:
            {
                "tipo": "deslocamento",  # deslocamento, formula, texto, numero
                "km": 45,
                "usar_gmaps": true,
                "pedagio": 12.50,
            }
            ou:
            {
                "tipo": "formula",
                "formula": "km * 2.50 + IPCA_E"
            }
        processo: Objeto Processo (para cálculos)

    Returns:
        {
            "campo": "{{DESLOCAMENTO}}",
            "valor_final": "45 km",
            "tipo": "deslocamento",
            "metadata": {...}
        }

    Raises:
        ValueError: Se o mapeamento é inválido
    """
    if not campo or not valor_input:
        raise ValueError("campo e valor_input são obrigatórios")

    tipo = valor_input.get("tipo", "texto").lower()

    if tipo == "deslocamento":
        return _validar_deslocamento(campo, valor_input, processo)
    elif tipo == "formula":
        return _validar_formula(campo, valor_input, processo)
    elif tipo == "numero":
        return _validar_numero(campo, valor_input)
    elif tipo == "texto":
        return _validar_texto(campo, valor_input)
    else:
        raise ValueError(f"Tipo de mapeamento desconhecido: {tipo}")


def _mes_extenso(m: int) -> str:
    """Retorna o nome do mês em português extenso."""
    meses = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    return meses[m] if 1 <= m <= 12 else ""


def _valor_br(v) -> str:
    """Formata valor em reais (R$ 1.234,56)."""
    if v is None:
        return ""
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return ""


def _validar_deslocamento(campo: str, valor_input: dict, processo=None) -> dict:
    """Valida mapeamento de tipo 'deslocamento'."""
    km = valor_input.get("km")
    if km is None:
        raise ValueError(f"{campo}: km é obrigatório para tipo deslocamento")

    try:
        km = float(km)
    except (ValueError, TypeError):
        raise ValueError(f"{campo}: km deve ser um número válido")

    if km < 0:
        raise ValueError(f"{campo}: km não pode ser negativo")

    usar_gmaps = valor_input.get("usar_gmaps", False)
    pedagio = valor_input.get("pedagio", 0)

    try:
        pedagio = float(pedagio)
    except (ValueError, TypeError):
        pedagio = 0

    # Valor padrão: R$ 2.50 por km (pode ser customizado)
    taxa_km = valor_input.get("taxa_km", 2.50)
    try:
        taxa_km = float(taxa_km)
    except (ValueError, TypeError):
        taxa_km = 2.50

    valor_final = (km * taxa_km) + pedagio

    return {
        "campo": campo,
        "valor_final": f"{km} km + {_valor_br(pedagio)}",
        "valor_numerico": valor_final,
        "tipo": "deslocamento",
        "metadata": {
            "km": km,
            "taxa_km": taxa_km,
            "pedagio": pedagio,
            "usar_gmaps": usar_gmaps,
            "valor_calculado": _valor_br(valor_final),
        }
    }


def _validar_formula(campo: str, valor_input: dict, processo=None) -> dict:
    """
    P0: Valida mapeamento de tipo 'formula' com simpleeval (sem eval).

    Restrições:
    - Apenas operadores aritméticos: +, -, *, /, %
    - Apenas funções whitelisted: abs, round, max, min
    - Sem acesso a builtins ou variáveis arbitrárias

    Args:
        campo: Nome do campo
        valor_input: Dict com 'formula' (string)
        processo: Objeto processo (para futuras variáveis)

    Returns:
        Dict com campo, valor_final, tipo, metadata

    Raises:
        ValueError: Se fórmula é inválida ou contém código perigoso
    """
    try:
        from simpleeval import EvalWithCompoundTypes
    except ImportError:
        raise ImportError("simpleeval não instalado. Execute: pip install simpleeval")

    formula = valor_input.get("formula")
    if not formula:
        raise ValueError(f"{campo}: formula é obrigatória para tipo formula")

    # P0: Rejeita palavras-chave perigosas explicitamente
    forbidden_keywords = ["__", "import", "exec", "eval", "lambda", "class", "def"]
    for keyword in forbidden_keywords:
        if keyword in formula:
            raise ValueError(f"{campo}: fórmula contém código perigoso: '{keyword}'")

    # P0: Whitelist de funções matemáticas seguras
    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "max": max,
        "min": min,
    }

    # Substitui variáveis conhecidas com números
    formula_safe = formula
    if "IPCA_E" in formula:
        # TODO: buscar IPCA-E real do dia via API de economia
        ipca_e = 1.05  # placeholder
        formula_safe = formula_safe.replace("IPCA_E", str(ipca_e))

    try:
        # P0: simpleeval avalia apenas expressões seguras
        # Não permite atribuição, statements, ou acesso a variáveis não whitelistadas
        evaluator = EvalWithCompoundTypes(functions=ALLOWED_FUNCTIONS, names={})
        resultado = evaluator.eval(formula_safe)

        # Valida que o resultado é numérico
        if not isinstance(resultado, (int, float)):
            raise ValueError(f"{campo}: fórmula deve retornar número, retornou {type(resultado)}")

    except ValueError as e:
        # Re-lança ValueErrors de validação
        if "contém código perigoso" in str(e):
            raise
        raise ValueError(f"{campo}: fórmula inválida: {str(e)}")
    except Exception as e:
        # Captura erros de simpleeval (sintaxe, operador desconhecido, etc)
        raise ValueError(f"{campo}: fórmula inválida: {str(e)}")

    return {
        "campo": campo,
        "valor_final": str(resultado),
        "tipo": "formula",
        "metadata": {
            "formula": formula,
            "formula_processada": formula_safe,
            "resultado": resultado,
        }
    }


def _validar_numero(campo: str, valor_input: dict) -> dict:
    """Valida mapeamento de tipo 'numero'."""
    valor = valor_input.get("valor")
    if valor is None:
        raise ValueError(f"{campo}: valor é obrigatório para tipo numero")

    try:
        valor_num = float(valor)
    except (ValueError, TypeError):
        raise ValueError(f"{campo}: valor deve ser um número válido")

    return {
        "campo": campo,
        "valor_final": valor_input.get("formato", str(valor_num)),
        "valor_numerico": valor_num,
        "tipo": "numero",
        "metadata": {
            "valor": valor_num,
            "formato": valor_input.get("formato", str(valor_num)),
        }
    }


def _validar_texto(campo: str, valor_input: dict) -> dict:
    """Valida mapeamento de tipo 'texto'."""
    valor = valor_input.get("valor", "")
    if not isinstance(valor, str):
        valor = str(valor)

    return {
        "campo": campo,
        "valor_final": valor,
        "tipo": "texto",
        "metadata": {
            "valor": valor,
            "comprimento": len(valor),
        }
    }
