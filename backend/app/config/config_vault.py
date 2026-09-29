"""
Azure Key Vault Integration — config.py
Settings class com fallback automático .env
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    logger.warning("Azure SDK not installed. Will use .env fallback only.")


class Settings(BaseSettings):
    # App
    app_name: str = os.getenv("APP_NAME", "Perito System v6.0")
    app_version: str = os.getenv("APP_VERSION", "6.0.0")
    environment: str = os.getenv("ENVIRONMENT", "development")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./v6.db")

    # JWT — from Vault or .env
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

    # CORS
    cors_origins: list = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://129.121.34.186,https://sistema.ipcms.com.br"
        ).split(",")
    ]

    # Azure Vault config
    azure_vault_url: str = os.getenv("AZURE_VAULT_URL", "")
    azure_vault_name: str = os.getenv("AZURE_VAULT_NAME", "ipcms-perito-secrets")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_secret_from_vault(self, secret_name: str) -> Optional[str]:
        """
        Get secret from Azure Key Vault with fallback to .env

        Args:
            secret_name: Secret name (e.g., "GRAPH-CLIENT-SECRET")

        Returns:
            Secret value or None
        """
        if not VAULT_AVAILABLE:
            logger.warning(f"Vault unavailable for {secret_name}, using .env fallback")
            return os.getenv(secret_name.replace("-", "_"))

        try:
            vault_url = f"https://{self.azure_vault_name}.vault.azure.net/"
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)
            secret = client.get_secret(secret_name)
            logger.info(f"✅ Retrieved {secret_name} from Vault")
            return secret.value
        except Exception as e:
            logger.warning(f"⚠️ Vault error for {secret_name}: {e}. Using .env fallback.")
            return os.getenv(secret_name.replace("-", "_"))


# Singleton instance
settings = Settings()
