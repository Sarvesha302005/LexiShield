"""
PayPal Webhook Security and Signature Validation.
Validates incoming PayPal webhook events using X.509 certificates and RSA signatures.
"""

import base64
import logging
import re
import zlib
from collections.abc import Mapping
from urllib.parse import urlparse

import httpx
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from src.core.config import get_settings
from src.core.exceptions import (
    InvalidCertificateUrlError,
    InvalidSignatureError,
    WebhookVerificationError,
)

logger = logging.getLogger(__name__)

# In-memory certificate cache: cert_url -> x509.Certificate
_CERT_CACHE: dict[str, x509.Certificate] = {}

# Allowed PayPal domain regex for certificate URLs to prevent SSRF
# Matches *.paypal.com with https protocol
PAYPAL_CERT_HOST_PATTERN = re.compile(r"^(?:[a-zA-Z0-9-]+\.)*paypal\.com$", re.IGNORECASE)


def validate_cert_url(cert_url: str) -> None:
    """
    Validate that the certificate URL is HTTPS and hosted on an official PayPal domain.
    Prevents Server-Side Request Forgery (SSRF) and malicious cert injection.
    """
    if not cert_url:
        raise InvalidCertificateUrlError("Certificate URL is missing.")

    parsed = urlparse(cert_url)
    if parsed.scheme.lower() != "https":
        raise InvalidCertificateUrlError(
            f"Insecure certificate URL scheme '{parsed.scheme}'. HTTPS is strictly required."
        )

    hostname = parsed.hostname or ""
    if not PAYPAL_CERT_HOST_PATTERN.match(hostname):
        raise InvalidCertificateUrlError(
            f"Untrusted certificate host '{hostname}'. Must be an authorized *.paypal.com domain."
        )


def compute_crc32(raw_body: bytes) -> int:
    """
    Compute unsigned 32-bit CRC32 checksum for raw body bytes.
    Matches PayPal's specification for webhook payload hashing.
    """
    return zlib.crc32(raw_body) & 0xFFFFFFFF


def build_signature_payload(
    transmission_id: str,
    transmission_time: str,
    webhook_id: str,
    raw_body: bytes,
) -> bytes:
    """
    Construct the string of data that PayPal signed.
    Format: <transmission_id>|<transmission_time>|<webhook_id>|<crc32(raw_body)>
    """
    crc = compute_crc32(raw_body)
    data_string = f"{transmission_id}|{transmission_time}|{webhook_id}|{crc}"
    return data_string.encode("utf-8")


async def get_certificate(
    cert_url: str, client: httpx.AsyncClient | None = None
) -> x509.Certificate:
    """
    Retrieve and parse the X.509 certificate from the URL, using in-memory cache.
    """
    validate_cert_url(cert_url)

    if cert_url in _CERT_CACHE:
        return _CERT_CACHE[cert_url]

    try:
        if client:
            resp = await client.get(cert_url, timeout=10.0)
            resp.raise_for_status()
            cert_pem = resp.content
        else:
            async with httpx.AsyncClient() as session:
                resp = await session.get(cert_url, timeout=10.0)
                resp.raise_for_status()
                cert_pem = resp.content

        cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
        _CERT_CACHE[cert_url] = cert
        return cert
    except httpx.HTTPError as exc:
        logger.error(f"Failed to fetch PayPal certificate from {cert_url}: {exc}")
        raise WebhookVerificationError(f"Failed to retrieve certificate: {exc}") from exc
    except Exception as exc:
        logger.error(f"Failed to parse X.509 certificate from {cert_url}: {exc}")
        raise WebhookVerificationError(f"Invalid X.509 certificate data: {exc}") from exc


async def verify_paypal_webhook_signature(
    headers: Mapping[str, str],
    raw_body: bytes,
    webhook_id: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """
    Verify PayPal Webhook signature based on headers and raw body.

    Required Headers:
    - PAYPAL-AUTH-ALGO
    - PAYPAL-TRANSMISSION-ID
    - PAYPAL-CERT-URL
    - PAYPAL-TRANSMISSION-SIG
    - PAYPAL-TRANSMISSION-TIME
    """
    settings = get_settings()
    configured_webhook_id = webhook_id or settings.PAYPAL_WEBHOOK_ID

    # Header normalization (case-insensitive dictionary lookup)
    normalized = {k.upper(): v for k, v in headers.items()}

    auth_algo = normalized.get("PAYPAL-AUTH-ALGO")
    transmission_id = normalized.get("PAYPAL-TRANSMISSION-ID")
    cert_url = normalized.get("PAYPAL-CERT-URL")
    transmission_sig = normalized.get("PAYPAL-TRANSMISSION-SIG")
    transmission_time = normalized.get("PAYPAL-TRANSMISSION-TIME")

    # Allow mock bypass in testing / dev if strict verification is disabled
    if not settings.STRICT_WEBHOOK_VERIFICATION:
        logger.info("Bypassing webhook signature check (STRICT_WEBHOOK_VERIFICATION=false).")
        return True

    missing = [
        name
        for name, val in [
            ("PAYPAL-AUTH-ALGO", auth_algo),
            ("PAYPAL-TRANSMISSION-ID", transmission_id),
            ("PAYPAL-CERT-URL", cert_url),
            ("PAYPAL-TRANSMISSION-SIG", transmission_sig),
            ("PAYPAL-TRANSMISSION-TIME", transmission_time),
        ]
        if not val
    ]

    if missing:
        raise WebhookVerificationError(
            f"Missing required PayPal webhook headers: {', '.join(missing)}"
        )

    # Validate certificate and retrieve public key
    cert = await get_certificate(cert_url=cert_url, client=client)  # type: ignore[arg-type]
    public_key = cert.public_key()
    if not isinstance(public_key, RSAPublicKey):
        raise WebhookVerificationError("Unsupported certificate public key type; RSA required.")

    # Decode signature
    try:
        signature_bytes = base64.b64decode(transmission_sig)  # type: ignore[arg-type]
    except Exception as exc:
        raise InvalidSignatureError(f"Corrupted base64 signature: {exc}") from exc

    # Build signed string
    data_bytes = build_signature_payload(
        transmission_id=transmission_id,  # type: ignore[arg-type]
        transmission_time=transmission_time,  # type: ignore[arg-type]
        webhook_id=configured_webhook_id,
        raw_body=raw_body,
    )

    # Determine hash algorithm from auth_algo (e.g. SHA256withRSA)
    if "SHA256" in auth_algo.upper():  # type: ignore[union-attr]
        hash_algo = hashes.SHA256()
    elif "SHA1" in auth_algo.upper():  # type: ignore[union-attr]
        hash_algo = hashes.SHA1()  # type: ignore[assignment]
    else:
        raise WebhookVerificationError(f"Unsupported algorithm '{auth_algo}'.")

    # Cryptographic verification
    try:
        public_key.verify(
            signature_bytes,
            data_bytes,
            padding.PKCS1v15(),
            hash_algo,
        )
        logger.debug(f"Signature successfully verified for transmission {transmission_id}.")
        return True
    except InvalidSignature as exc:
        logger.warning(f"Invalid PayPal webhook signature for transmission {transmission_id}.")
        raise InvalidSignatureError("PayPal webhook signature verification failed.") from exc
    except Exception as exc:
        logger.error(f"Error during cryptographic verification: {exc}")
        raise WebhookVerificationError(f"Signature verification error: {exc}") from exc
