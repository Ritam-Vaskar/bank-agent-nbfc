# TrustLend shared contracts

## 1. Scope

This document is normative for all TrustLend modules. If a module specification
conflicts with this document, the implementation must record an explicit exception
before coding.

## 2. Decision boundary

The LLM may:

- ask for missing information;
- classify a user's conversational intent through a constrained schema;
- explain deterministic results using approved facts and templates.

The LLM must not:

- approve, reject, price, calculate, schedule, disburse, or alter a loan;
- receive raw Aadhaar, PAN, OTP, access tokens, database credentials, or secrets;
- invent values not present in the deterministic result;
- override a policy, fraud flag, credential proof, ledger state, or audit failure.

The following engines remain authoritative:

| Concern | Authority |
|---|---|
| KYC/credential verification | KYC verifier |
| Eligibility | Policy engine |
| Affordability | Affordability engine |
| Risk | Risk engine plus fraud service |
| Pricing and EMI | Pricing and EMI engines |
| Acceptance | Strict intent classifier plus explicit user action |
| Disbursement and collection | Payments service and PostgreSQL ledger |
| Audit history | Append-only audit service and verifier |

## 3. Identifiers and time

- All new event IDs, transaction IDs, credential IDs, and verification IDs are
  UUIDs.
- Persist timestamps as UTC ISO-8601 values with timezone information.
- Monetary values use integer minor units (`amount_paise`) in ledger contracts.
  Existing Mongo offer fields may remain decimal-compatible during migration, but
  payment boundaries must convert once and preserve exactness.
- Hashes are lowercase hexadecimal SHA-256 strings unless a contract says otherwise.

## 4. Privacy classes

| Class | Examples | Permitted handling |
|---|---|---|
| Secret | JWT, API keys, private keys, OTP | Never log; never send to an LLM; secret manager only |
| Direct PII | Aadhaar, PAN, email, phone, DOB | Encrypted at rest; redacted before LLM; masked in UI/logs |
| Derived sensitive | income, credit score, FOIR, risk score | Minimize and purpose-limit; no raw values in prompts unless required |
| Public verification | signed hash, issuer DID, credential status | May be externally verifiable |

Every audit metadata field must declare its privacy class in code review. Raw direct
PII in `conversation_messages`, logs, prompts, metrics labels, or error text is a
release blocker.

## 5. Event envelope

All modules emit audit events with:

```json
{
  "event_id": "uuid",
  "event_type": "trustlend.module.action",
  "occurred_at": "UTC timestamp",
  "actor_type": "user|system|admin|issuer|scheduler",
  "actor_id": "non-secret identifier or null",
  "application_id": "uuid or null",
  "loan_id": "uuid or null",
  "payload": {},
  "schema_version": 1
}
```

The audit service adds `prev_hash` and `entry_hash`; producers must not set either
field.

## 6. Failure policy

Fail closed for identity, authorization, policy, output verification, audit-chain
verification, ledger posting, key retrieval, revocation, and sovereign egress
controls. A user-friendly response may be generated, but it must describe an
incomplete or blocked operation and must not look like success.

## 7. Cross-module release gates

- No raw PII appears in an LLM request fixture or captured prompt.
- A deterministic offer and an explanation cannot disagree on principal, rate, EMI,
  tenure, fee, or repayment total.
- Every money movement has a balanced ledger transaction and an idempotency key.
- Every critical state transition creates an audit event.
- Security tests cover both allow and deny paths.
