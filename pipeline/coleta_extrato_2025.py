import os
import requests
import json
from datetime import datetime
from typing import List, Dict
import sys
import pathlib

# Adiciona o diretório do script (pipeline) ao path para importar config
sys.path.append(str(pathlib.Path(__file__).parent))
from config import OLLAMA_MODEL, OLLAMA_TIMEOUT, EMAIL_MONITOR_ENABLED, EMAIL_USER, EMAIL_PASSWORD, VPS_HOST, VPS_USER, VPS_PASSWORD, CHROMA_DIR, RAG_N_EXEMPLOS, ONE_DRIVE_DIR, CONVENIDOS

class ColetaExtrato2025:
    def __init__(self, client_id: str, client_secret: str, cert_path: str, key_path: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cert_path = cert_path
        self.key_path = key_path
        self.base_url = "https://api.bancointer.com.br"
        self.access_token = None

    def obter_token(self) -> str:
        """Obtém token de acesso OAuth2."""
        if self.access_token:
            return self.access_token
        
        # Verifica se os certificados existem
        if not os.path.exists(self.cert_path) or not os.path.exists(self.key_path):
            raise FileNotFoundError(f"Certificados não encontrados em {self.cert_path} ou {self.key_path}")

        # Implementação simplificada de OAuth2
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/oauth/v2/token",
                headers=headers,
                data=data,
                cert=(self.cert_path, self.key_path)
            )
            response.raise_for_status()
            self.access_token = response.json()['access_token']
            return self.access_token
        except Exception as e:
            raise Exception(f"Erro ao obter token: {str(e)}")

    def obter_extrato(self, mes: int, ano: int) -> List[Dict]:
        """Obtém o extrato bancário para um mês específico."""
        token = self.obter_token()
        
        # Data de início e fim do mês
        inicio = f"{ano}-{mes:02d}-01"
        if mes == 12:
            fim = f"{ano + 1}-01-01"
        else:
            fim = f"{ano}-{mes + 1:02d}-01"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'dataInicial': inicio,
            'dataFinal': fim
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/extrato/v1/contas-correntes",
                headers=headers,
                params=params,
                cert=(self.cert_path, self.key_path)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Erro ao obter extrato: {str(e)}")

# Exemplo de uso
if __name__ == "__main__":
    # Configurações de exemplo (substituir por variáveis de ambiente)
    # Para uso real, estas devem vir do .env ou de um gerenciador de segredos
    client_id = os.getenv("INTER_CLIENT_ID", "seu_client_id")
    client_secret = os.getenv("INTER_CLIENT_SECRET", "seu_client_secret")
    cert_path = os.getenv("INTER_CERT_PATH", "/caminho/para/certificado.crt")
    key_path = os.getenv("INTER_KEY_PATH", "/caminho/para/chave_privada.key")
    
    # Verifica se as variáveis de ambiente estão definidas
    if client_id == "seu_client_id" or client_secret == "seu_client_secret":
        print("⚠️ Aviso: Credenciais do Banco Inter não configuradas no .env. Usando valores de exemplo.")
    
    coletor = ColetaExtrato2025(client_id, client_secret, cert_path, key_path)
    
    # Obter extrato de maio/2025
    try:
        extrato = coletor.obter_extrato(5, 2025)
        print(f"Extrato de maio/2025: {len(extrato)} transações")
        for transacao in extrato:
            print(f"  - {transacao.get('descricao', 'N/A')}: R$ {transacao.get('valor', 'N/A')}")
    except Exception as e:
        print(f"❌ Erro ao coletar extrato: {e}")
