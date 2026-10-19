# Security Policy & Vulnerability Disclosure

## Supported Versions

LexiShield takes financial data integrity and cryptographic verification seriously. Security updates and patches are actively maintained for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

---

## Cryptographic Security Architecture

LexiShield enforces institutional zero-trust security controls across all external ingress boundaries:

1. **PayPal Webhook Authenticity:**
   - Enforces strict X.509 certificate chain validation.
   - Prevents Server-Side Request Forgery (SSRF) by validating that certificate URLs originate exclusively from `*.paypal.com` over HTTPS.
   - Caches public keys with TTL to prevent replay attacks and cryptographic verification latency.
   - Verifies RSA SHA-256 signatures over `transmission_id|timestamp|webhook_id|crc32(body)`.

2. **Tenant Isolation & Secret Management:**
   - Multi-tenant data structures partition disputes, audit trails, and risk configurations by `merchant_id`.
   - Bring-Your-Own-Credentials (BYOK) secrets (PayPal Client ID, Secret, Webhook Listener Key) are stored encrypted at rest and never emitted into logs or client-facing responses.

3. **Pre-Dispute Deflection Safeguards:**
   - Card network alert streams (Ethoca / Verifi) require HMAC signature verification before automated refund execution.

---

## Reporting a Vulnerability

If you discover a security vulnerability within LexiShield, please **do not report it via public GitHub issues**. Instead, please follow our responsible disclosure process:

1. Email our security response team at **security@lexishield.dev** (or open a confidential security advisory directly on GitHub).
2. Include detailed technical information:
   - Summary and type of vulnerability (e.g., SSRF, replay attack, signature bypass).
   - Step-by-step reproduction instructions or a minimal Proof of Concept (PoC).
   - Affected components, endpoints, or dependencies.
   - Potential impact on merchant funds or data privacy.

### Response Timeline
* **Initial Acknowledgment:** Within 24 hours of receipt.
* **Assessment & Severity Triaging:** Within 48 hours.
* **Patch Release & Advisory:** Within 5 business days for critical vulnerabilities.

We appreciate the security research community's efforts in keeping open-source fintech software secure.
