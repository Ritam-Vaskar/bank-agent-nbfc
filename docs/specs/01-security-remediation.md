# Security remediation specification

## Scope

This is the prerequisite workstream for TrustLend. It corrects discrepancies between
the current implementation and its documentation before new modules are added.

## Requirements

### PII-safe LLM boundary

1. Add a single guard used by every LLM invocation, including collection, offer
   explanation, rejection, follow-up, Telegram, and future provider adapters.
2. Detect and replace Aadhaar, PAN, OTP, email, phone, bank-account, card, and
   access-token patterns before the request is built.
3. Enforce a configurable character and message-count limit. Reject oversize input
   with an explicit validation response.
4. Persist the redacted transcript for LLM context; retain raw input only in the
   encrypted application boundary when business-required.
5. Record a non-sensitive `pii_redaction_applied` event without recording the match.

### Strict intent contract

Replace keyword checks in `routes/loans.py` with:

```json
{
  "intent": "continue|accept|reject|question",
  "confidence": 0.0,
  "needs_clarification": true,
  "reason": "short non-sensitive rationale"
}
```

Only exact `accept` or `reject` with confidence at or above the configured threshold
may advance or decline a decision gate. Ambiguous input must ask:
“Did you mean to decline the offer?” and must not change workflow state. `no` alone is
ambiguous, not rejection. Reset and terminate remain explicit non-decision controls.

### Authentication

- Issue the JWT in a `Secure`, `HttpOnly`, `SameSite=Lax` cookie scoped to the API.
- Do not return the access token to JavaScript or persist it in localStorage.
- Update backend dependencies to read and validate the cookie; keep a temporary
  Authorization-header compatibility flag only for migration.
- Add CSRF protection for cookie-authenticated state-changing requests.
- Logout must clear the cookie and blacklist the token when available.
- Remove auth token and user data from browser localStorage. Application chat state
  may remain persisted only after a privacy review; raw PII must not be persisted.

### Encryption and network hardening

- Replace the claim “AES-256 Fernet” with the actual algorithm until migration is
  complete: Fernet is AES-128-CBC with HMAC.
- Target AES-256-GCM through a versioned encryption envelope:
  `{version, key_id, nonce, ciphertext, tag}`.
- Never expose MongoDB `27017` or Redis `6379` in host port mappings in production.
  Internal services use authenticated TLS endpoints or a private network.
- Production ingress exposes only the TLS reverse proxy and required application
  ports.

## Interfaces

- `POST /api/auth/verify-otp`: sets auth cookie; response contains user profile only.
- `POST /api/auth/logout`: clears auth cookie.
- `POST /api/loans/applications/{id}/chat`: accepts user message and returns a
  redacted response plus intent clarification when needed.
- `GET /api/security/redaction-status`: admin-only operational status, no payloads.

## Acceptance criteria

- A prompt containing valid-looking Aadhaar/PAN produces no raw identifier in the
  provider request, stored conversation, log, or error.
- “yes”, “accept the offer”, and an explicit UI accept action can accept; “no”,
  “maybe”, and “I have a question” cannot.
- Browser JavaScript cannot read the auth cookie, and an XSS-style localStorage read
  finds no JWT.
- Ciphertext decrypts only with the versioned AES-256-GCM envelope.
- Production compose has no public MongoDB or Redis port.
