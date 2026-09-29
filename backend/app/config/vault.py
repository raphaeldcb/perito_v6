"""
Azure Key Vault Integration for Perito v6
Secure secrets management with automatic fallback to .env
"""

import os
import logging
from typing import Optional, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)

try:
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient
    from azure.core.exceptions import AzureError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    # Dummy class for when Azure SDK is not available
    class AzureError(Exception):  # type: ignore
        pass
    logger.warning("Azure SDK not installed. Will use .env fallback only.")


class SecretManager:
    """
    Manages secrets from Azure Key Vault with automatic fallback to .env

    Usage:
        from app.config.vault import secrets

        db_url = secrets.get_secret("DATABASE-URL")
        api_key = secrets.get_secret("GRAPH-CLIENT-SECRET")

    Features:
        - Automatic caching to reduce API calls
        - Fallback to .env if Vault unavailable
        - Support for both hyphenated and underscore-separated keys
        - Logging for audit trail
    """

    def __init__(self, vault_name: Optional[str] = None):
        """
        Initialize SecretManager

        Args:
            vault_name: Azure Key Vault name (e.g., 'ipcms-perito-secrets')
                       If None, reads from AZURE_VAULT_NAME env var
        """
        self.vault_name = vault_name or os.getenv("AZURE_VAULT_NAME", "ipcms-perito-secrets")
        self.vault_url = f"https://{self.vault_name}.vault.azure.net/"
        self._cache: Dict[str, str] = {}
        self._client: Optional[SecretClient] = None
        self._initialized = False

        if AZURE_AVAILABLE and os.getenv("AZURE_VAULT_URL"):
            self._initialize_vault()
        else:
            logger.info("Azure Key Vault not configured. Using .env fallback mode.")

    def _initialize_vault(self) -> None:
        """Initialize Azure Key Vault client with appropriate credentials"""
        if not AZURE_AVAILABLE:
            logger.warning("Azure SDK not available. Vault initialization skipped.")
            return

        try:
            # Try managed identity first (production VPS)
            try:
                credential = ManagedIdentityCredential()
                logger.info("Using Managed Identity credential for Azure Key Vault")
            except Exception:
                # Fallback to default credential (local dev, service principal)
                credential = DefaultAzureCredential()
                logger.info("Using DefaultAzureCredential for Azure Key Vault")

            self._client = SecretClient(vault_url=self.vault_url, credential=credential)
            self._initialized = True
            logger.info(f"✅ Azure Key Vault initialized: {self.vault_name}")

        except AzureError as e:
            logger.warning(f"⚠️ Failed to initialize Azure Key Vault: {e}")
            logger.info("Switching to .env fallback mode")
            self._initialized = False
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error initializing Azure Key Vault: {e}")
            self._initialized = False

    def get_secret(self, key: str) -> Optional[str]:
        """
        Get secret from vault or .env fallback

        Args:
            key: Secret name (can use hyphens or underscores, e.g., "DATABASE-URL" or "database_url")

        Returns:
            Secret value or None if not found

        Raises:
            ValueError: If key is empty or invalid
        """
        if not key or not isinstance(key, str):
            logger.error(f"Invalid key: {key}")
            return None

        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Try Vault
        if self._initialized and self._client:
            try:
                secret = self._client.get_secret(key)
                self._cache[key] = secret.value
                logger.debug(f"✅ Retrieved '{key}' from Azure Key Vault (cached)")
                return secret.value
            except AzureError as e:
                logger.warning(f"⚠️ Vault error for '{key}': {e}")
            except Exception as e:
                logger.warning(f"⚠️ Unexpected error retrieving '{key}' from Vault: {e}")

        # Fallback to .env
        env_key = key.replace("-", "_").upper()
        value = os.getenv(env_key)
        if value:
            self._cache[key] = value
            logger.debug(f"✅ Retrieved '{key}' from .env (cached)")
            return value

        logger.warning(f"⚠️ Secret '{key}' not found in Vault or .env")
        return None

    def get_secret_or_raise(self, key: str, error_msg: Optional[str] = None) -> str:
        """
        Get secret or raise ValueError if not found

        Args:
            key: Secret name
            error_msg: Custom error message

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found
        """
        value = self.get_secret(key)
        if not value:
            msg = error_msg or f"Required secret '{key}' not found in Vault or .env"
            logger.error(msg)
            raise ValueError(msg)
        return value

    def list_secrets(self) -> Dict[str, str]:
        """
        List all secrets from cache (for debugging only)

        Returns:
            Dictionary of cached secrets

        Note:
            This only returns cached secrets, not all secrets in the vault
        """
        return self._cache.copy()

    def clear_cache(self) -> None:
        """Clear the secret cache (for testing or manual refresh)"""
        self._cache.clear()
        logger.info("Secret cache cleared")

    def health_check(self) -> Dict[str, any]:
        """
        Check vault health and connectivity

        Returns:
            Dictionary with health status
        """
        status = {
            "vault_available": AZURE_AVAILABLE,
            "vault_initialized": self._initialized,
            "vault_name": self.vault_name,
            "cache_size": len(self._cache),
        }

        if self._initialized and self._client:
            try:
                # Try to get a secret to verify connectivity
                self._client.get_secret("DATABASE-URL")
                status["vault_connected"] = True
            except Exception as e:
                status["vault_connected"] = False
                status["vault_error"] = str(e)

        return status


# Singleton instance — use this throughout the app
_secret_manager = None


def get_secret_manager() -> SecretManager:
    """
    Get or create the singleton SecretManager instance

    Returns:
        SecretManager instance
    """
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


# Convenience module-level instance
secrets = get_secret_manager()
