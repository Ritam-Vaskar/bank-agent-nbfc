# Signed sanction letter specification

## Goal

Make a generated sanction letter independently verifiable and detect edits after
issuance.

## Signing

- Generate the PDF from the authoritative offer, EMI schedule, application ID, and
  loan ID only after final acceptance and checks.
- Compute SHA-256 over the exact PDF bytes.
- Sign a canonical verification payload with an Ed25519 private key held outside the
  application image:

```json
{
  "loan_id": "uuid",
  "letter_hash": "64-char hex",
  "issued_at": "UTC timestamp",
  "key_id": "sanction-key-2026-01",
  "schema_version": 1
}
```

- Embed the signature, key ID, and a QR code linking to
  `/verify/{loan_id}?hash={letter_hash}`. The QR must not contain PII.
- Publish the public key through a versioned endpoint or trusted key bundle.

## Verification

`GET /verify/{loan_id}` returns:

```json
{
  "valid": true,
  "loan_id": "uuid",
  "letter_hash": "64-char hex",
  "signature_valid": true,
  "terms_match": true,
  "key_id": "sanction-key-2026-01",
  "verified_at": "UTC timestamp"
}
```

The verifier checks signature, key validity, loan status, and hash equality. A
missing, edited, revoked, or mismatched document returns `valid: false` with a
stable reason code and no sensitive loan details.

## Key operations

- Keep old public keys available for the verification lifetime of issued letters.
- Rotate signing keys with an overlap period.
- Audit issuance, key rotation, verification, and invalid verification attempts.
- Store the immutable PDF bytes in the approved object store; local disk is
  development-only.

## Acceptance criteria

- A genuine PDF scans to `valid`.
- Changing one byte causes `letter_hash` or signature validation to fail.
- A forged QR pointing at another loan does not validate.
- Key rotation does not invalidate letters signed by retained historical keys.
