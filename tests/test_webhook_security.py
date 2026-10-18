"""
Unit tests for PayPal Webhook Security and Signature Validation.
"""

import json

import pytest

from src.core.exceptions import (
    InvalidCertificateUrlError,
    InvalidSignatureError,
    WebhookVerificationError,
)
from src.core.security import (
    compute_crc32,
    validate_cert_url,
    verify_paypal_webhook_signature,
)


def test_validate_cert_url_valid():
    """Verify official PayPal HTTPS domains pass validation."""
    validate_cert_url("https://api.paypal.com/v1/notifications/certs/CERT-123.pem")
    validate_cert_url("https://api.sandbox.paypal.com/certs/cert.pem")
    validate_cert_url("https://notify.paypal.com/cert.pem")


def test_validate_cert_url_insecure_scheme():
    """Verify HTTP scheme raises InvalidCertificateUrlError."""
    with pytest.raises(InvalidCertificateUrlError, match="HTTPS is strictly required"):
        validate_cert_url("http://api.paypal.com/cert.pem")


def test_validate_cert_url_ssrf_attacks():
    """Verify malicious hostnames and domain spoofing are rejected."""
    # Attacker controlled domain
    with pytest.raises(InvalidCertificateUrlError, match="Untrusted certificate host"):
        validate_cert_url("https://evil.com/cert.pem")

    # Subdomain spoofing attempt
    with pytest.raises(InvalidCertificateUrlError, match="Untrusted certificate host"):
        validate_cert_url("https://api.paypal.com.attacker.com/cert.pem")

    # Missing cert URL
    with pytest.raises(InvalidCertificateUrlError, match="Certificate URL is missing"):
        validate_cert_url("")


def test_compute_crc32():
    """Verify unsigned 32-bit CRC32 checksum calculation."""
    payload = b'{"test":"hello world"}'
    crc = compute_crc32(payload)
    assert isinstance(crc, int)
    assert crc > 0


@pytest.mark.asyncio
async def test_verify_valid_signature(sign_webhook_payload):
    """Test cryptographic verification succeeds with matching signature and cert."""
    raw_payload = json.dumps({"event": "CUSTOMER.DISPUTE.CREATED"}).encode("utf-8")
    headers = sign_webhook_payload(raw_payload)

    is_valid = await verify_paypal_webhook_signature(
        headers=headers,
        raw_body=raw_payload,
        webhook_id="TEST_WEBHOOK_ID_001",
    )
    assert is_valid is True


@pytest.mark.asyncio
async def test_verify_tampered_payload_rejected(sign_webhook_payload):
    """Test signature fails if the body is tampered with after signing."""
    original_payload = json.dumps({"event": "CUSTOMER.DISPUTE.CREATED"}).encode("utf-8")
    headers = sign_webhook_payload(original_payload)

    # Tampered body
    tampered_payload = json.dumps({"event": "CUSTOMER.DISPUTE.CREATED", "tampered": True}).encode(
        "utf-8"
    )

    with pytest.raises(InvalidSignatureError, match="signature verification failed"):
        await verify_paypal_webhook_signature(
            headers=headers,
            raw_body=tampered_payload,
            webhook_id="TEST_WEBHOOK_ID_001",
        )


@pytest.mark.asyncio
async def test_verify_missing_headers_rejected():
    """Test rejection when critical verification headers are missing."""
    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        # Missing transmission id, cert url, signature, etc.
    }
    with pytest.raises(WebhookVerificationError, match="Missing required PayPal webhook headers"):
        await verify_paypal_webhook_signature(
            headers=headers,
            raw_body=b"{}",
        )


@pytest.mark.asyncio
async def test_verify_untrusted_cert_url_rejected(sign_webhook_payload):
    """Test that an untrusted cert URL in headers triggers InvalidCertificateUrlError."""
    raw_payload = b'{"test":1}'
    headers = sign_webhook_payload(raw_payload)
    headers["PAYPAL-CERT-URL"] = "https://attacker.org/fake_cert.pem"

    with pytest.raises(InvalidCertificateUrlError):
        await verify_paypal_webhook_signature(
            headers=headers,
            raw_body=raw_payload,
        )
