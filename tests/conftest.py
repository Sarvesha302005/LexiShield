"""
Pytest configuration, shared fixtures, mock generators, and sample dispute payloads.
"""

import base64
import datetime
import os
from collections.abc import AsyncGenerator

# Keep tests offline even when real keys are in .env: environment variables take precedence over
# .env, so every Settings() built during the run (including in tests) sees placeholder keys.
os.environ["OPENROUTER_API_KEY"] = "mock_openrouter_api_key"
os.environ["NVIDIA_API_KEY"] = "mock_nvidia_api_key"
os.environ["LEXISHIELD_DB_PATH"] = "test_lexishield.db"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_lexishield.db"
import shutil
from typing import Any

import httpx
import pytest
import pytest_asyncio
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from src.core.config import get_settings
from src.core.security import _CERT_CACHE, build_signature_payload
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure tests execute inside an isolated test_lexishield.db so lexishield.db is never polluted."""
    test_db = "test_lexishield.db"
    prod_db = "lexishield.db"
    if os.path.exists(prod_db):
        shutil.copyfile(prod_db, test_db)
    yield
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def override_settings():
    """Ensure test settings are active and clean cache."""
    _CERT_CACHE.clear()
    settings = get_settings()
    settings.ENVIRONMENT = "test"
    settings.STRICT_WEBHOOK_VERIFICATION = True
    settings.PAYPAL_WEBHOOK_ID = "TEST_WEBHOOK_ID_001"
    # Keep tests offline even when real keys are in .env (otherwise tests call the providers).
    settings.OPENROUTER_API_KEY = "mock_openrouter_api_key"
    settings.NVIDIA_API_KEY = "mock_nvidia_api_key"
    settings.SQLITE_DB_PATH = "test_lexishield.db"
    settings.DATABASE_URL = "sqlite+aiosqlite:///./test_lexishield.db"
    return settings


@pytest.fixture(scope="session")
def test_rsa_keypair():
    """Generate in-memory RSA keypair for cryptographic testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(scope="session")
def test_x509_cert(test_rsa_keypair):
    """Generate self-signed X.509 cert in memory for PayPal signature validation tests."""
    private_key, public_key = test_rsa_keypair
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PayPal Inc Mock"),
            x509.NameAttribute(NameOID.COMMON_NAME, "api.paypal.com"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    return cert


@pytest.fixture
def sign_webhook_payload(test_rsa_keypair, test_x509_cert):
    """Helper fixture to sign a webhook payload using PayPal's cryptographic format."""
    private_key, _ = test_rsa_keypair
    cert_url = "https://api.paypal.com/v1/notifications/certs/CERT-TEST-123.pem"
    # Pre-cache cert to avoid real HTTP call
    _CERT_CACHE[cert_url] = test_x509_cert

    def _sign(
        payload_bytes: bytes,
        webhook_id: str = "TEST_WEBHOOK_ID_001",
        transmission_id: str = "TRANS-ID-987654321",
        transmission_time: str = "2026-10-18T12:00:00Z",
    ) -> dict[str, str]:
        data_to_sign = build_signature_payload(
            transmission_id=transmission_id,
            transmission_time=transmission_time,
            webhook_id=webhook_id,
            raw_body=payload_bytes,
        )
        sig = private_key.sign(
            data_to_sign,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        b64_sig = base64.b64encode(sig).decode("utf-8")

        return {
            "PAYPAL-AUTH-ALGO": "SHA256withRSA",
            "PAYPAL-TRANSMISSION-ID": transmission_id,
            "PAYPAL-CERT-URL": cert_url,
            "PAYPAL-TRANSMISSION-SIG": b64_sig,
            "PAYPAL-TRANSMISSION-TIME": transmission_time,
            "Content-Type": "application/json",
        }

    return _sign


@pytest.fixture
def sample_inquiry_payload() -> dict[str, Any]:
    """Sample dispute created payload at INQUIRY stage."""
    return {
        "id": "WH-EVT-INQUIRY-001",
        "event_version": "1.0",
        "create_time": "2026-10-18T10:00:00Z",
        "resource_type": "dispute",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "summary": "Customer initiated an inquiry regarding order status.",
        "resource": {
            "dispute_id": "PP-D-INQUIRY-9001",
            "create_time": "2026-10-18T09:55:00Z",
            "dispute_stage": "INQUIRY",
            "dispute_reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "dispute_amount": {
                "currency_code": "USD",
                "value": "89.00",
            },
            "disputed_transactions": [
                {
                    "seller_transaction_id": "TXN-INQ-8899",
                    "invoice_number": "ORD-INQ-8899",
                    "gross_amount": {"currency_code": "USD", "value": "89.00"},
                    "buyer": {"name": "Jordan Smith", "email": "jordan.smith@example.com"},
                }
            ],
        },
    }


@pytest.fixture
def sample_claim_high_pwin_payload() -> dict[str, Any]:
    """Sample dispute created payload at CLAIM stage with strong defense evidence (P_win >= 0.70)."""
    return {
        "id": "WH-EVT-CLAIM-HIGH-002",
        "event_version": "1.0",
        "create_time": "2026-10-18T11:00:00Z",
        "resource_type": "dispute",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "summary": "Customer escalated dispute to a claim.",
        "resource": {
            "dispute_id": "PP-D-DEFEND-7701",
            "create_time": "2026-10-18T10:45:00Z",
            "dispute_stage": "CLAIM",
            "dispute_reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "dispute_amount": {
                "currency_code": "USD",
                "value": "199.00",
            },
            "disputed_transactions": [
                {
                    "seller_transaction_id": "TXN-DEF-7701",
                    "invoice_number": "ORD-DEF-7701",
                    "gross_amount": {"currency_code": "USD", "value": "199.00"},
                    "buyer": {"name": "Taylor Ray", "email": "taylor.ray@example.com"},
                }
            ],
        },
    }


@pytest.fixture
def sample_claim_low_pwin_payload() -> dict[str, Any]:
    """Sample dispute created payload at CLAIM stage with weak evidence (P_win < 0.70)."""
    return {
        "id": "WH-EVT-CLAIM-LOW-003",
        "event_version": "1.0",
        "create_time": "2026-10-18T11:30:00Z",
        "resource_type": "dispute",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "summary": "Customer filed claim for lost item.",
        "resource": {
            "dispute_id": "PP-D-CONCEDE-3301",
            "create_time": "2026-10-18T11:15:00Z",
            "dispute_stage": "CLAIM",
            "dispute_reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "dispute_amount": {
                "currency_code": "USD",
                "value": "65.00",
            },
            "disputed_transactions": [
                {
                    "seller_transaction_id": "TXN-CONCEDE-LOST-3301",
                    "invoice_number": "ORD-CONCEDE-LOST-3301",
                    "gross_amount": {"currency_code": "USD", "value": "65.00"},
                    "buyer": {"name": "Morgan Lee", "email": "morgan.lee@example.com"},
                }
            ],
        },
    }


@pytest.fixture
def sample_claim_hitl_high_value_payload() -> dict[str, Any]:
    """Sample dispute payload with order value > $300 triggering HITL review."""
    return {
        "id": "WH-EVT-HITL-004",
        "event_version": "1.0",
        "create_time": "2026-10-18T12:00:00Z",
        "resource_type": "dispute",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "summary": "High value dispute claim created.",
        "resource": {
            "dispute_id": "PP-D-HITL-5501",
            "create_time": "2026-10-18T11:50:00Z",
            "dispute_stage": "CLAIM",
            "dispute_reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "dispute_amount": {
                "currency_code": "USD",
                "value": "750.00",  # Exceeds $300 threshold
            },
            "disputed_transactions": [
                {
                    "seller_transaction_id": "TXN-HITL-5501",
                    "invoice_number": "ORD-HITL-5501",
                    "gross_amount": {"currency_code": "USD", "value": "750.00"},
                    "buyer": {"name": "Casey VIP", "email": "casey.vip@example.com"},
                }
            ],
        },
    }


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
