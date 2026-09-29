"""Service layer for CNAB payment generation."""
import logging
from typing import Dict, List, Any
from .schemas import BeneficiarioPagamento, GerarCNABRequest
from .core import gerar_cnab240

logger = logging.getLogger(__name__)


class ColetadorService:
    """Business logic for CNAB payment generation."""

    @staticmethod
    def get_empresa_config() -> Dict[str, str]:
        """Get IPCMS company configuration for CNAB."""
        return {
            "cnpj": "14424142000190",
            "agencia": "00001",
            "conta": "4335168",
            "dv_conta": "9",
            "nome": "IPCMS",
            "nome_banco": "BANCO INTER"
        }

    @staticmethod
    def validar_beneficiarios(beneficiarios: List[BeneficiarioPagamento]) -> Dict[str, Any]:
        """Valida lista de beneficiários."""
        if not beneficiarios:
            raise ValueError("Lista de beneficiários vazia")

        total = sum(b.valor for b in beneficiarios)

        # Validar campos
        for i, b in enumerate(beneficiarios):
            if len(b.nome) < 1 or len(b.nome) > 30:
                raise ValueError(f"Beneficiário {i}: nome deve ter 1-30 chars")
            if not b.cpf.isdigit() or len(b.cpf) != 11:
                raise ValueError(f"Beneficiário {i}: CPF inválido")
            if b.valor <= 0:
                raise ValueError(f"Beneficiário {i}: valor deve ser > 0")

        return {
            "status": "validado",
            "beneficiarios": len(beneficiarios),
            "valor_total": total / 100,
            "mensagens": []
        }

    @staticmethod
    def gerar_cnab(request: GerarCNABRequest) -> Dict[str, Any]:
        """Gera arquivo CNAB240 para pagamento de coletadores."""
        from datetime import datetime

        dados_empresa = ColetadorService.get_empresa_config()
        data_pag = request.data_pagamento or datetime.now().strftime("%d%m%Y")

        # Converter Pydantic para dict para compatibilidade
        beneficiarios = [b.model_dump() for b in request.beneficiarios]

        # Gerar CNAB
        linhas, total_valor = gerar_cnab240(dados_empresa, beneficiarios, data_pag)

        # Validar CNAB gerado
        if not linhas or len(linhas) < 6:
            raise ValueError("CNAB gerado inválido (< 6 linhas)")

        for i, linha in enumerate(linhas):
            if len(linha) != 240:
                logger.warning(f"Linha {i} tem {len(linha)} chars, esperava 240")

        # Criar nome arquivo
        agora = datetime.now().strftime("%d%m%Y%H%M%S")
        nome_arquivo = f"CI240_001_{agora}.rem"

        logger.info(
            f"CNAB gerado: {len(beneficiarios)} beneficiários, "
            f"R$ {total_valor/100:.2f}, arquivo={nome_arquivo}"
        )

        return {
            "status": "sucesso",
            "arquivo": nome_arquivo,
            "beneficiarios": len(beneficiarios),
            "valor_total": total_valor / 100,
            "linhas": len(linhas),
            "data_pagamento": data_pag,
            "conteudo_preview": linhas[:2] if linhas else []
        }
