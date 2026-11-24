# Verifiable credentials and KYC specification

## Goal

Allow a borrower to prove policy-relevant facts without uploading or repeatedly
exposing source identity documents. Existing Aadhaar/PAN verification remains a
fallback until this flow is production-equivalent.

## Trust model

- An issuer owns an Ed25519 signing key and a `did:web` identifier.
- The issuer publishes its public key and verification method at
  `/.well-known/did.json`.
- A wallet stores credentials locally and sends only a verifier presentation.
- The verifier validates signature, issuer trust, audience, expiry, nonce, schema,
  and revocation before returning claims.
- The lender trusts only configured issuer DIDs and key versions.

Use an SD-JWT VC-compatible representation where feasible. If the prototype uses a
reduced format, it must document the unsupported SD-JWT features and must not call
the result production selective disclosure.

## Credential claims

Minimum mock credential schemas:

- `age_over_21`: boolean predicate proof, without date of birth.
- `monthly_income_over_25000`: boolean predicate proof, without exact salary.
- `identity_binding`: stable subject binding, without raw Aadhaar/PAN.

Claims are scoped to a verifier audience and application purpose. The issuer must
not place PAN or Aadhaar in a disclosed claim for the target flow.

## Components

### Issuer

- `POST /issuer/credentials`: authenticated mock issuer endpoint.
- `GET /.well-known/did.json`: public DID document.
- `GET /issuer/revocations/{credential_id}`: status or signed status list.
- Key rotation keeps old public keys available until all issued credentials expire.

### Wallet

- Next.js wallet page displays issuer, type, expiry, and disclosed claims.
- Credentials are encrypted in browser storage where supported; no private issuer
  key is ever delivered to the browser.
- The borrower selects claims; the wallet creates a nonce-bound presentation.
- Wallet UI clearly states when fallback document KYC is being used.

### Verifier and workflow

`verify_kyc_node` accepts either a credential presentation or the legacy KYC input.
The result includes:

```json
{
  "method": "verifiable_credential|legacy_document",
  "verified": true,
  "claims": {"age_over_21": true, "monthly_income_over_25000": true},
  "issuer_did": "did:web:issuer.example",
  "credential_id": "uuid",
  "checked_at": "UTC timestamp"
}
```

The policy engine consumes proofs such as `age_over_21`, not raw values. Proof
failure, expiry, audience mismatch, unknown issuer, or revocation is a hard KYC
failure and is audited without storing the presentation.

## Acceptance criteria

- A valid presentation passes without an Aadhaar/PAN upload.
- A tampered claim, wrong audience, expired credential, rotated unknown key, and
  revoked credential all fail closed.
- The verifier can prove the policy input was a credential proof.
- Browser storage and audit records contain no raw source document.
- Legacy fallback remains functional and visibly marked.
