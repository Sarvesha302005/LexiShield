"""
Configuration management using Pydantic Settings.
Loads configuration from environment variables and .env files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for PayPal Dispute Engine."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PROJECT_NAME: str = "PayPal Dispute Resolution Engine"
    API_V1_STR: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./lexishield.db",
        description="Async database connection URL (SQLite for local dev, PostgreSQL for production)",
    )
    SQLITE_DB_PATH: str = Field(
        default="lexishield.db",
        description="File path for direct SQLite operations",
    )

    # PayPal API Settings
    PAYPAL_MODE: Literal["sandbox", "live"] = "sandbox"
    PAYPAL_CLIENT_ID: str = "mock_paypal_client_id"
    PAYPAL_CLIENT_SECRET: str = "mock_paypal_client_secret"
    PAYPAL_WEBHOOK_ID: str = "mock_paypal_webhook_id"
    PAYPAL_API_BASE_URL: str = "https://api-m.sandbox.paypal.com"
    STRICT_WEBHOOK_VERIFICATION: bool = True

    # Google Gemini / OpenRouter 3-Tier LLM Orchestration Settings
    GEMINI_API_KEY: str = "mock_gemini_api_key"
    GEMINI_MODEL: str = "google/gemini-2.0-flash-thinking-exp:free"

    OPENROUTER_API_KEY: str = "mock_openrouter_api_key"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_PRIMARY_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    OPENROUTER_FALLBACK_MODEL: str = "nvidia/nemotron-3.5-super-vl:free"
    OPENROUTER_TIMEOUT_SECONDS: float = 25.0
    OPENROUTER_SITE_URL: str = "https://lexishield.io"
    OPENROUTER_APP_NAME: str = "LexiShield Dispute Defense Engine"
    # Used as a third, cross-provider backup when NVIDIA NIM is the primary provider.
    OPENROUTER_BACKUP_MODEL: str = "nvidia/nemotron-3.5-super-vl:free"

    # NVIDIA NIM (build.nvidia.com). When a real key is set, NIM serves Tier 1 and Tier 2
    # and OpenRouter becomes the backup; without one, OpenRouter serves Tier 1 and Tier 2.
    NVIDIA_API_KEY: str = "mock_nvidia_api_key"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    # Dispute analysis (formal rebuttal, win probability): quality first.
    NVIDIA_PRIMARY_MODEL: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    NVIDIA_FALLBACK_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    # Buyer conversation (merchant replies, simulated buyer): speed first. Bolt answered in about
    # 1.5 s in benchmarks against 20+ s for the larger models; replies stay short and factual.
    NVIDIA_CHAT_PRIMARY_MODEL: str = "nvidia/nemotron-3.5-bolt-e4b"
    NVIDIA_CHAT_FALLBACK_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    NVIDIA_CHAT_TIMEOUT_SECONDS: float = 45.0
    # New-dispute analysis prompts are long; Super VL needed more than 40 s for them on NIM.
    NVIDIA_TIMEOUT_SECONDS: float = 90.0

    # Tries per model when it returns an empty answer. Free NIM/OpenRouter models occasionally do
    # (Nemotron 3 Ultra answered about 3 in 8 requests), and a quick retry usually succeeds.
    LLM_EMPTY_RESPONSE_ATTEMPTS: int = 3

    # Financial & Fee Parameters
    STANDARD_DISPUTE_FEE: float = Field(default=15.00, description="Standard dispute fee in USD")
    HIGH_VOLUME_DISPUTE_FEE: float = Field(
        default=30.00, description="High-volume/high-ratio dispute fee in USD"
    )
    HIGH_DISPUTE_FEE_THRESHOLD_MONTHLY_DISPUTES: int = Field(
        default=100, description="Dispute count threshold triggering high volume dispute fee"
    )
    HIGH_RISK_TENANT_ANOMALY_THRESHOLD: float = Field(
        default=0.015,
        description="Merchant dispute ratio threshold (1.5%) triggering high-risk anomaly HITL gate",
    )

    # Decision Engine Thresholds & Universal Defense Policy
    SELLER_RIGHTS_FIRST_ENABLED: bool = Field(
        default=True,
        description="Enforces Universal Defense Policy: defend any ticket size when valid seller rights proof exists",
    )
    DEFEND_P_WIN_THRESHOLD: float = Field(
        default=0.70, description="Minimum P(win) required to automatically defend claims"
    )
    HITL_ORDER_VALUE_THRESHOLD: float = Field(
        default=300.00, description="Order value triggering mandatory HITL review"
    )
    HITL_P_WIN_LOWER: float = Field(
        default=0.60, description="Lower P(win) boundary triggering HITL review"
    )
    HITL_P_WIN_UPPER: float = Field(
        default=0.75, description="Upper P(win) boundary triggering HITL review"
    )

    # Security & Storage
    SECRET_KEY: str = "super-secret-key-change-in-production-1234567890"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()


def get_sqlite_db_path() -> str:
    """Return active SQLite database file path, honoring LEXISHIELD_DB_PATH override if set."""
    import os

    env_path = os.environ.get("LEXISHIELD_DB_PATH")
    if env_path:
        return env_path
    return get_settings().SQLITE_DB_PATH
