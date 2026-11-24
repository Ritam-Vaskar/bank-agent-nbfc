# Sovereign cloud mode specification

## Goal

Provide an explicit mode in which customer data and model inference stay within an
approved region and outbound destinations are deny-by-default.

## Provider abstraction

Configuration:

```text
LLM_PROVIDER=groq|openai|local
SOVEREIGN_MODE=true|false
SOVEREIGN_REGION=ap-south-1
ALLOWED_EGRESS_DOMAINS=...
```

All providers implement the same interface: redacted messages in, structured
response out, timeout and usage metadata returned. Local mode uses Ollama or vLLM
with a pinned model image and no external fallback.

Sovereign mode must reject startup if `local` is not selected unless an explicitly
approved in-region provider is configured and tested.

## Egress

- Route backend outbound traffic through Squid or Envoy.
- OPA policy denies all destinations not on the approved domain list when sovereign
  mode is enabled.
- DNS resolution and direct-IP egress are controlled by the proxy/network policy.
- Blocked calls return an explicit error and emit a non-sensitive audit event.
- CI and the demo include an allowed call and a blocked external call.

## Residency and deployment

- Target AWS `ap-south-1` for the prototype.
- Infrastructure policy denies resources outside the approved region.
- MongoDB, Redis, object storage, logs, metrics, and model artifacts need an
  explicit residency classification.
- Region status is reported from deployment configuration and a live compliance
  check; a static environment flag alone is insufficient.

## Envelope encryption

- Generate a per-record data-encryption key.
- Encrypt the record with AES-256-GCM.
- Wrap the data key with KMS or Vault Transit and store only the wrapped key,
  key ID, nonce, tag, and ciphertext.
- Key rotation rewraps data keys without exposing plaintext.
- The legacy single `ENCRYPTION_KEY` path is migration-only and disabled in
  sovereign production.

## Acceptance criteria

- Switching sovereign mode to local inference causes no provider request outside
  the approved boundary.
- A non-approved outbound domain is blocked by policy, not application convention.
- A deliberate direct-IP bypass is blocked.
- Residency checks show compliant and non-compliant test deployments correctly.
- A record remains decryptable after key rotation and is unreadable without KMS/Vault.
