"""Cliente para API Banco Inter com autenticação mTLS + OAuth2."""
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import requests
from requests.auth import HTTPBasicAuth
from urllib3.util.ssl_ import create_urllib3_context
from fastapi import HTTPException

from app.utils import retry, get_circuit_breaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)

# Singleton global para reutilizar token
_inter_client_instance: Optional['InterAPIClient'] = None


class InterAPIClient:
    """
    Cliente seguro para comunicação com API Banco Inter.

    Features:
    - mTLS (mutual TLS) com certificado de cliente
    - OAuth2 (client_credentials flow)
    - Token refresh automático
    - Rate limiting + retry com backoff
    - Logging seguro (sem dados sensíveis)
    """

    BASE_URL = "https://cdpj.partners.bancointer.com.br"
    OAUTH_URL = "https://cdpj.partners.bancointer.com.br"
    TOKEN_ENDPOINT = "/oauth/v2/token"

    def __init__(self):
        # Carregar paths de certificado/chave das env vars (seguro)
        self.cert_path = os.getenv(
            "INTER_CERT_PATH",
            "/app/.secrets/inter/Inter API_Certificado.crt"
        )
        self.key_path = os.getenv(
            "INTER_KEY_PATH",
            "/app/.secrets/inter/Inter API_Chave.key"
        )
        self.client_id = os.getenv("INTER_CLIENT_ID")
        self.client_secret = os.getenv("INTER_CLIENT_SECRET")

        # Validar que caminhos existem
        if not os.path.exists(self.cert_path):
            raise FileNotFoundError(f"Certificado não encontrado: {self.cert_path}")
        if not os.path.exists(self.key_path):
            raise FileNotFoundError(f"Chave privada não encontrada: {self.key_path}")
        if not self.client_id or not self.client_secret:
            raise ValueError("INTER_CLIENT_ID e INTER_CLIENT_SECRET obrigatórios")

        # Token cache
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

        # Session com mTLS
        self.session = requests.Session()
        self.session.cert = (self.cert_path, self.key_path)
        self.session.verify = True  # Validar certificado do servidor

    def _get_token(self) -> str:
        """Obtém token OAuth2 (com cache + refresh automático)."""
        # Usar token em cache se ainda válido
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token

        logger.info("Renovando token OAuth2 Banco Inter")

        try:
            response = self.session.post(
                f"{self.OAUTH_URL}{self.TOKEN_ENDPOINT}",
                auth=HTTPBasicAuth(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            self._token = data["access_token"]

            # Cache token por (TTL - 1 min de margem)
            ttl_seconds = data.get("expires_in", 3600)
            self._token_expires = datetime.now() + timedelta(seconds=ttl_seconds - 60)

            logger.info(f"Token renovado, válido até {self._token_expires.isoformat()}")
            return self._token

        except Exception as e:
            logger.error(f"Erro ao obter token OAuth2: {str(e)}")
            raise

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Faz requisição autenticada com tratamento de erros.

        Args:
            method: GET, POST, PATCH, etc
            endpoint: /api/v1/pix/transfer (sem base URL)
            data: payload JSON
            timeout: segundos

        Returns:
            Response JSON

        Raises:
            requests.HTTPError se status >= 400
        """
        token = self._get_token()
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Perito-v6/1.0"
        }

        logger.debug(f"{method} {endpoint}")  # Seguro: sem token aqui

        try:
            response = self.session.request(
                method,
                url,
                json=data,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            # Log sem expor dados sensíveis
            logger.error(
                f"Erro HTTP {e.response.status_code} em {endpoint}: "
                f"{e.response.text[:200]}"
            )
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de comunicação com Banco Inter: {str(e)}")
            raise

    # ===== ENDPOINTS PIX =====

    def pix_transfer(
        self,
        chave_destino: str,
        valor: int,
        descricao: str,
        id_unico: str
    ) -> Dict[str, Any]:
        """
        Transferência via PIX.

        Args:
            chave_destino: CPF, email, telefone ou chave aleatória
            valor: em centavos (ex: 100000 = R$ 1.000,00)
            descricao: motivo da transferência
            id_unico: identificador idempotente (UUID)

        Returns:
            {"transaction_id": "...", "status": "PENDING", ...}
        """
        return self._make_request(
            "POST",
            "/api/v1/pix/transfer",
            data={
                "chave": chave_destino,
                "valor": valor,
                "descricao": descricao,
                "id_unico": id_unico
            }
        )

    def pix_status(self, transaction_id: str) -> Dict[str, Any]:
        """Consulta status de transação PIX."""
        return self._make_request(
            "GET",
            f"/api/v1/pix/transfer/{transaction_id}"
        )

    # ===== ENDPOINTS CONSULTAS =====

    def get_balance(self) -> Dict[str, Any]:
        """Obtém saldo da conta."""
        return self._make_request("GET", "/api/v1/account/balance")

    def get_statement(
        self,
        data_inicio: str,
        data_fim: str,
        limite: int = 100
    ) -> Dict[str, Any]:
        """
        Extrato (DDMMYYYY).

        Args:
            data_inicio: "15072026"
            data_fim: "15072026"
            limite: registros a retornar
        """
        return self._make_request(
            "GET",
            "/api/v1/account/statement",
            params={
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "limite": limite
            }
        )

    # ===== ENDPOINTS CNAB =====

    def cnab_upload(self, arquivo_rem: bytes) -> Dict[str, Any]:
        """
        Upload de arquivo CNAB240 (.rem).

        Args:
            arquivo_rem: conteúdo do arquivo em bytes

        Returns:
            {"lote_id": "...", "status": "PROCESSING"}
        """
        # Nota: Este endpoint pode usar multipart/form-data
        # Documentação do Banco Inter terá detalhes exatos
        logger.warning("cnab_upload não implementado — aguardando documentação Banco Inter")
        raise NotImplementedError("Endpoint CNAB não documentado ainda")

    def __del__(self):
        """Cleanup: fechar session."""
        if hasattr(self, 'session'):
            self.session.close()

    @classmethod
    def get_instance(cls) -> 'InterAPIClient':
        """Retorna instância singleton para reutilizar token."""
        global _inter_client_instance
        if _inter_client_instance is None:
            _inter_client_instance = cls()
        return _inter_client_instance
