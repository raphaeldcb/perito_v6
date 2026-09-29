import os
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file="/app/.env",
        extra="ignore",  # Ignore undefined env vars
        case_sensitive=False,  # OLLAMA_URL → ollama_url
    )

    # App Configuration
    app_name: str = os.getenv("APP_NAME", "Perito System v6.0")
    app_version: str = os.getenv("APP_VERSION", "6.0.0")
    environment: Literal["development", "production"] = os.getenv("ENVIRONMENT", "development")  # type: ignore

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./v6.db")
    database_echo: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"

    # JWT Security — CRITICAL: Change in production
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # CORS — Explicit, no wildcards
    # Origins: localhost (dev), VPS direct access, production domain
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://129.121.34.186,https://sistema.ipcms.com.br"
        ).split(",")
    ]
    cors_credentials: bool = os.getenv("CORS_CREDENTIALS", "True").lower() == "true"
    # Methods: Only necessary verbs (no * wildcard)
    cors_methods: list[str] = [
        method.strip()
        for method in os.getenv("CORS_METHODS", "GET,POST,PATCH,DELETE").split(",")
    ]
    # Headers: Only required headers (no * wildcard)
    cors_headers: list[str] = [
        header.strip()
        for header in os.getenv("CORS_HEADERS", "Content-Type,Authorization").split(",")
    ]

    # Qwen LLM
    qwen_api_key: str = Field(default="", validation_alias="QWEN_API_KEY")
    qwen_model: str = Field(default="qwen-turbo", validation_alias="QWEN_MODEL")
    ollama_url: str = Field(default="http://172.17.0.1:11435", validation_alias="OLLAMA_URL")

    # Agent Authentication (Windows/Mac agents)
    agent_api_key: str = os.getenv("AGENT_API_KEY", "")

    # Azure / Office 365 Graph API
    graph_tenant_id: str = os.getenv("GRAPH_TENANT_ID", "")
    graph_client_id: str = os.getenv("GRAPH_CLIENT_ID", "")
    graph_client_secret: str = os.getenv("GRAPH_CLIENT_SECRET", "")
    graph_mailbox: str = os.getenv("GRAPH_MAILBOX", "admin@ipcms.com.br")
    onedrive_tenant: str = os.getenv("ONEDRIVE_TENANT", "")

    # Azure (alternative names for same credentials)
    azure_client_id: str = os.getenv("AZURE_CLIENT_ID", "")
    azure_client_secret: str = os.getenv("AZURE_CLIENT_SECRET", "")
    azure_tenant_id: str = os.getenv("AZURE_TENANT_ID", "")
    azure_vault_name: str = os.getenv("AZURE_VAULT_NAME", "ipcms-perito-secrets")

    # Inter Bank API (payments)
    inter_client_id: str = os.getenv("INTER_CLIENT_ID", "")
    inter_client_secret: str = os.getenv("INTER_CLIENT_SECRET", "")
    inter_api_url: str = os.getenv("INTER_API_URL", "")

    # Google Maps API
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    google_client_secret_path: str = os.getenv("GOOGLE_CLIENT_SECRET_PATH", "")

    # File Storage (PDF/uploads)
    storage_dir: str = os.getenv("STORAGE_DIR", "/data")

    # Rate Limiting (slowapi format: "N/period")
    rate_limit_login: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    rate_limit_search: str = os.getenv("RATE_LIMIT_SEARCH", "30/minute")
    rate_limit_upload: str = os.getenv("RATE_LIMIT_UPLOAD", "5/minute")

    # Event Bus & Task Queue (Task 15 — Wave 2)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Auditoria & Logging
    audit_retention_days: int = int(os.getenv("AUDIT_RETENTION_DAYS", "90"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # OneDrive Sync (Phase 3)
    onedrive_folder_path: str = os.getenv("ONEDRIVE_FOLDER_PATH", "/drive/root:/IPCMS - ARQUIVOS/MODELOS")
    onedrive_sync_enabled: bool = os.getenv("ONEDRIVE_SYNC_ENABLED", "false").lower() == "true"
    onedrive_sync_interval: str = os.getenv("ONEDRIVE_SYNC_INTERVAL", "daily")
    onedrive_sync_hour: str = os.getenv("ONEDRIVE_SYNC_HOUR", "02:00")

    # Feedback & Error Reporting System — Task 4 (deploy automático 19h UTC)
    # DESABILITADO por padrão: liga o scheduler (thread) no startup do backend.
    feedback_deploy_enabled: bool = os.getenv("FEEDBACK_DEPLOY_ENABLED", "false").lower() == "true"
    # DRY-RUN por padrão: mesmo com o scheduler ligado, não executa git/docker
    # de verdade até alguém desligar explicitamente (ver feedback_scheduler.py).
    feedback_deploy_dry_run: bool = os.getenv("FEEDBACK_DEPLOY_DRY_RUN", "true").lower() == "true"
    feedback_deploy_hour: str = os.getenv("FEEDBACK_DEPLOY_HOUR", "19:00")
    backend_health_url: str = os.getenv("BACKEND_HEALTH_URL", "http://localhost:8000/health")
    vps_backend_path: str = os.getenv("VPS_BACKEND_PATH", "/var/www/perito-v6/backend")
    vps_git_remote: str = os.getenv("VPS_GIT_REMOTE", "vps")
    vps_git_branch: str = os.getenv("VPS_GIT_BRANCH", "main")
    docker_backend_container: str = os.getenv("DOCKER_BACKEND_CONTAINER", "perito-v6-backend")

    # Forensic Analysis APIs (3-layer: local + 6 external + synthesis)
    ibm_watson_api_key: str = os.getenv("IBM_WATSON_API_KEY", "")
    google_vision_api_key: str = os.getenv("GOOGLE_VISION_API_KEY", "")
    reality_defender_key: str = os.getenv("REALITY_DEFENDER_KEY", "")
    azure_computer_vision_key: str = os.getenv("AZURE_COMPUTER_VISION_KEY", "")

    # Fake Detector Combo — 6 APIs (70% Consenso)
    deepware_api_key: str = os.getenv("DEEPWARE_API_KEY", "")
    azure_video_indexer_key: str = os.getenv("AZURE_VIDEO_INDEXER_KEY", "")
    azure_video_indexer_account_id: str = os.getenv("AZURE_VIDEO_INDEXER_ACCOUNT_ID", "")
    google_cloud_credentials_json: str = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON", "")
    google_cloud_access_token: str = os.getenv("GOOGLE_CLOUD_ACCESS_TOKEN", "")
    reality_defender_api_key: str = os.getenv("REALITY_DEFENDER_API_KEY", "")
    sensity_api_key: str = os.getenv("SENSITY_API_KEY", "")
    hume_api_key: str = os.getenv("HUME_API_KEY", "")

    # Sightengine (deepfake detection)
    sightengine_user: str = os.getenv("SIGHTENGINE_USER", "")
    sightengine_secret: str = os.getenv("SIGHTENGINE_SECRET", "")


settings = Settings()
