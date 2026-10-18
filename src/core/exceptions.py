"""
Domain-specific custom exceptions for the PayPal Dispute Resolution Engine.
"""

from typing import Any


class PayPalDisputeEngineException(Exception):
    """Base exception for all dispute engine errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class WebhookVerificationError(PayPalDisputeEngineException):
    """Raised when PayPal webhook signature verification fails."""


class InvalidCertificateUrlError(WebhookVerificationError):
    """Raised when the PayPal certificate URL does not belong to a trusted PayPal domain."""


class InvalidSignatureError(WebhookVerificationError):
    """Raised when the cryptographic signature does not match the payload digest."""


class DisputeNotFoundError(PayPalDisputeEngineException):
    """Raised when a referenced dispute does not exist in the engine repository."""


class DisputeAlreadyProcessedError(PayPalDisputeEngineException):
    """Raised when an incoming dispute event has already been processed (idempotency)."""


class CarrierTelemetryError(PayPalDisputeEngineException):
    """Raised when fetching carrier telemetry fails or data is corrupted."""


class WarehouseTelemetryError(PayPalDisputeEngineException):
    """Raised when retrieving warehouse packing telemetry fails."""


class OrderDBError(PayPalDisputeEngineException):
    """Raised when retrieving order transaction data fails."""


class ArbitrationError(PayPalDisputeEngineException):
    """Raised when LLM or heuristic arbitration evaluation fails."""


class PayPalAPIError(PayPalDisputeEngineException):
    """Raised when an external PayPal REST API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body


class PDFGenerationError(PayPalDisputeEngineException):
    """Raised when generating the evidentiary rebuttal PDF dossier fails."""


class HITLRequiredException(PayPalDisputeEngineException):
    """Raised or flagged when an automated action requires human-in-the-loop sign-off."""
