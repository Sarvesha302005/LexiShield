"""
Resilient Async PayPal Disputes REST API Client.
Implements OAuth2 token caching, exponential backoff retries, and dispute resolution endpoints.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from src.core.config import get_settings
from src.core.exceptions import PayPalAPIError

logger = logging.getLogger(__name__)


class PayPalClient:
    """Async client interacting with PayPal Disputes REST API."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.settings = get_settings()
        self._external_client = client
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client:
            return self._external_client
        return httpx.AsyncClient(timeout=30.0)

    async def get_access_token(self) -> str:
        """
        Retrieve cached OAuth2 Bearer token or fetch a new one using client credentials.
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        # Mock token for test environments
        if (
            self.settings.ENVIRONMENT in ("test", "development")
            and "mock" in self.settings.PAYPAL_CLIENT_ID.lower()
        ):
            self._access_token = "mock_access_token_bearer_12345"
            self._token_expires_at = now + 3600
            return self._access_token

        url = f"{self.settings.PAYPAL_API_BASE_URL}/v1/oauth2/token"
        headers = {"Accept": "application/json", "Accept-Language": "en_US"}
        data = {"grant_type": "client_credentials"}

        client = await self._get_client()
        try:
            resp = await client.post(
                url,
                data=data,
                headers=headers,
                auth=(self.settings.PAYPAL_CLIENT_ID, self.settings.PAYPAL_CLIENT_SECRET),
            )
            resp.raise_for_status()
            payload = resp.json()
            self._access_token = payload.get("access_token")
            expires_in = payload.get("expires_in", 3600)
            self._token_expires_at = now + float(expires_in)
            return self._access_token  # type: ignore[return-value]
        except Exception as exc:
            logger.error(f"Failed to authenticate with PayPal OAuth2: {exc}")
            raise PayPalAPIError(f"OAuth2 authentication failure: {exc}") from exc

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Execute HTTP request with exponential backoff and jitter for 429/5xx status codes."""
        token = await self.get_access_token()
        url = f"{self.settings.PAYPAL_API_BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "PayPal-Request-Id": correlation_id or f"REQ-{int(time.time() * 1000)}",
        }
        if not files:
            headers["Content-Type"] = "application/json"

        # Mock mode interception for local and test scenarios
        if "mock" in token:
            logger.info(f"[MOCK PAYPAL API] {method} {path} - Simulated success.")
            return {
                "status": "MOCK_SUCCESS",
                "method": method,
                "path": path,
                "dispute_id": path.split("/")[4] if len(path.split("/")) > 4 else "UNKNOWN",
                "simulated_time": time.time(),
            }

        client = await self._get_client()
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    files=files,
                    data=data,
                )

                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    delay = (2 ** (attempt - 1)) * 0.5
                    logger.warning(
                        f"PayPal API {resp.status_code} received. Retrying in {delay:.2f}s (Attempt {attempt}/{max_retries})."
                    )
                    await asyncio.sleep(delay)
                    continue

                resp.raise_for_status()
                return (
                    resp.json()
                    if resp.content
                    else {"status": "SUCCESS", "status_code": resp.status_code}
                )

            except httpx.HTTPStatusError as exc:
                if attempt >= max_retries:
                    body = exc.response.text if exc.response else ""
                    logger.error(
                        f"PayPal API error on {method} {url}: {exc.response.status_code} - {body}"
                    )
                    raise PayPalAPIError(
                        f"PayPal API HTTP {exc.response.status_code}",
                        status_code=exc.response.status_code,
                        response_body=body,
                    ) from exc
            except httpx.RequestError as exc:
                if attempt >= max_retries:
                    logger.error(f"Network error contacting PayPal API: {exc}")
                    raise PayPalAPIError(f"Network error communicating with PayPal: {exc}") from exc
                await asyncio.sleep(1.0)

        raise PayPalAPIError("Exhausted retries calling PayPal API.")

    async def send_message(
        self,
        dispute_id: str,
        message: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        POST /v1/customer/disputes/{dispute_id}/send-message
        Communicates with the customer to de-escalate an INQUIRY.
        """
        path = f"/v1/customer/disputes/{dispute_id}/send-message"
        payload = {"message": message}
        return await self._request_with_retry(
            method="POST",
            path=path,
            json_data=payload,
            correlation_id=correlation_id,
        )

    async def make_offer(
        self,
        dispute_id: str,
        offer_amount: float,
        note: str,
        offer_type: str = "REFUND",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        POST /v1/customer/disputes/{dispute_id}/make-offer
        Submits an offer (e.g. partial/full refund or replacement) to settle an INQUIRY.
        """
        path = f"/v1/customer/disputes/{dispute_id}/make-offer"
        payload = {
            "note": note,
            "offer_type": offer_type,
            "offer_amount": {
                "currency_code": "USD",
                "value": f"{offer_amount:.2f}",
            },
        }
        return await self._request_with_retry(
            method="POST",
            path=path,
            json_data=payload,
            correlation_id=correlation_id,
        )

    async def provide_evidence(
        self,
        dispute_id: str,
        pdf_bytes: bytes,
        notes: str,
        evidence_type: str = "PROOF_OF_DELIVERY",
        filename: str = "evidentiary_dossier.pdf",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        POST /v1/customer/disputes/{dispute_id}/provide-evidence
        Submits evidence (multipart/form-data with generated PDF) to defend a CLAIM.
        """
        path = f"/v1/customer/disputes/{dispute_id}/provide-evidence"
        files = {
            "file": (filename, pdf_bytes, "application/pdf"),
        }
        data = {
            "evidence_type": evidence_type,
            "notes": notes,
        }
        return await self._request_with_retry(
            method="POST",
            path=path,
            files=files,
            data=data,
            correlation_id=correlation_id,
        )

    async def accept_claim(
        self,
        dispute_id: str,
        note: str = "Merchant concedes claim upon preliminary financial review.",
        accept_claim_type: str = "REFUND",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        POST /v1/customer/disputes/{dispute_id}/accept-claim
        Concedes a CLAIM to avoid escalating dispute penalties.
        """
        path = f"/v1/customer/disputes/{dispute_id}/accept-claim"
        payload = {
            "note": note,
            "accept_claim_type": accept_claim_type,
        }
        return await self._request_with_retry(
            method="POST",
            path=path,
            json_data=payload,
            correlation_id=correlation_id,
        )
