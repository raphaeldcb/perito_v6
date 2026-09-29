"""Gerenciamento de certificados A1 (PKCS#12) — assinatura digital de XML."""
import json
import os
from typing import Optional, Dict, List
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend


class A1Manager:
    """Carrega e gerencia múltiplos certificados A1 do VPS."""

    def __init__(self):
        """Parse A1_CERTS_CONFIG do .env → dict de certificados."""
        config_str = os.getenv("A1_CERTS_CONFIG", "")
        self.certs: Dict[str, Dict] = {}
        self.default = os.getenv("A1_DEFAULT_CERT", "pesquisa")

        # Format: "pesquisa:1234567:/path/pesquisa.pfx:Instituto...|ipc-ms:12345678:/path/ipc-ms.pfx:IPC MS..."
        if config_str:
            for item in config_str.split("|"):
                parts = item.split(":")
                if len(parts) >= 4:
                    cert_id, password, path, razao_social = parts[0], parts[1], parts[2], ":".join(parts[3:])
                    self.certs[cert_id] = {
                        "id": cert_id,
                        "password": password.encode(),
                        "path": path,
                        "razao_social": razao_social.strip(),
                    }

    def get_cert_info(self, cert_id: Optional[str] = None) -> Dict:
        """Retorna metadata do certificado (sem carregar a chave privada)."""
        cert_id = cert_id or self.default
        if cert_id not in self.certs:
            raise ValueError(f"Certificado '{cert_id}' não encontrado. Disponíveis: {list(self.certs.keys())}")
        return self.certs[cert_id]

    def list_certs(self) -> List[Dict]:
        """Lista certificados disponíveis (público)."""
        return [
            {
                "id": cert_id,
                "razao_social": info["razao_social"],
                "disponivel": os.path.exists(info["path"])
            }
            for cert_id, info in self.certs.items()
        ]

    def load_cert_and_key(self, cert_id: Optional[str] = None):
        """Carrega certificado X.509 e chave privada do arquivo PKCS#12."""
        info = self.get_cert_info(cert_id)
        path = info["path"]
        password = info["password"]

        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo {path} não encontrado")

        with open(path, "rb") as f:
            pfx_data = f.read()

        # Desencripta PKCS#12
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            pfx_data, password, backend=default_backend()
        )

        return {
            "private_key": private_key,
            "certificate": certificate,
            "additional_certs": additional_certs,
            "id": cert_id or self.default,
            "razao_social": info["razao_social"],
        }
