"""
Domain-specific custom exceptions for the PayPal Dispute Resolution Engine.
"""

from typing import Any, Optional


class PayPalDisputeEngineException(Exception):
    """Base exception for all dispute engine errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class WebhookVerificationError(PayPalDisputeEngineException):
    """Raised when PayPal webhook signature verification fails."""
    pass


class InvalidCertificateUrlError(WebhookVerificationError):
    """Raised when the PayPal certificate URL does not belong to a trusted PayPal domain."""
    pass


class InvalidSignatureError(WebhookVerificationError):
    """Raised when the cryptographic signature does not match the payload digest."""
    pass


class DisputeNotFoundError(PayPalDisputeEngineException):
    """Raised when a referenced dispute does not exist in the engine repository."""
    pass


class DisputeAlreadyProcessedError(PayPalDisputeEngineException):
    """Raised when an incoming dispute event has already been processed (idempotency)."""
    pass


class CarrierTelemetryError(PayPalDisputeEngineException):
    """Raised when fetching carrier telemetry fails or data is corrupted."""
    pass


class WarehouseTelemetryError(PayPalDisputeEngineException):
    """Raised when retrieving warehouse packing telemetry fails."""
    pass


class OrderDBError(PayPalDisputeEngineException):
    """Raised when retrieving order transaction data fails."""
    pass


class ArbitrationError(PayPalDisputeEngineException):
    """Raised when LLM or heuristic arbitration evaluation fails."""
    pass


class PayPalAPIError(PayPalDisputeEngineException):
    """Raised when an external PayPal REST API request fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body


class PDFGenerationError(PayPalDisputeEngineException):
    """Raised when generating the evidentiary rebuttal PDF dossier fails."""
    pass


class HITLRequiredException(PayPalDisputeEngineException):
    """Raised or flagged when an automated action requires human-in-the-loop sign-off."""
    pass
