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

    # PayPal API Settings
    PAYPAL_MODE: Literal["sandbox", "live"] = "sandbox"
    PAYPAL_CLIENT_ID: str = "mock_paypal_client_id"
    PAYPAL_CLIENT_SECRET: str = "mock_paypal_client_secret"
    PAYPAL_WEBHOOK_ID: str = "mock_paypal_webhook_id"
    PAYPAL_API_BASE_URL: str = "https://api-m.sandbox.paypal.com"
    STRICT_WEBHOOK_VERIFICATION: bool = True

    # Google Gemini LLM Settings
    GEMINI_API_KEY: str = "mock_gemini_api_key"
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # OpenRouter LLM Settings
    OPENROUTER_API_KEY: str = "mock_openrouter_api_key"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Financial & Fee Parameters
    STANDARD_DISPUTE_FEE: float = Field(default=15.00, description="Standard dispute fee in USD")
    HIGH_VOLUME_DISPUTE_FEE: float = Field(
        default=30.00, description="High-volume/high-ratio dispute fee in USD"
    )
    HIGH_DISPUTE_FEE_THRESHOLD_MONTHLY_DISPUTES: int = Field(
        default=100, description="Dispute count threshold triggering high volume dispute fee"
    )

    # Decision Engine Thresholds
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
