# TrustLend specification set

## Purpose

This specification set turns the existing NBFC lending MVP into **TrustLend** without
changing the existing underwriting principle: the LLM may collect and explain, but
deterministic engines remain the only source of lending decisions and terms.

These specifications are implementation-ready contracts. They describe the target
behavior, boundaries, interfaces, security invariants, acceptance tests, and rollout
order. They do not claim that the target behavior already exists.

## Current baseline

The current runtime is:

- Next.js frontend with Zustand state and Axios API client.
- FastAPI backend with MongoDB and Redis.
- LangGraph loan workflow in `backend/workflows/loan_graph.py`.
- Deterministic KYC, bureau, policy, affordability, risk, pricing, EMI, and PDF
  engines.
- Groq-only `ChatGroq` construction in the active workflow.
- JWT passed in an `Authorization` header and persisted by the browser.
- Keyword-based stage intent handling in `backend/routes/loans.py`.
- MongoDB audit records without a hash-chain invariant.
- Simulated disbursement rather than a financial ledger.

## Specification index

| ID | Specification | Outcome |
|---|---|---|
| 00 | [Shared contracts](./00-shared-contracts.md) | Common terminology, boundaries, privacy rules, and release gates |
| 01 | [Security remediation](./01-security-remediation.md) | PII-safe LLM input, strict intents, cookie auth, corrected encryption and network exposure |
| 02 | [Tamper-evident audit trail](./02-tamper-evident-audit.md) | Hash-chained audit records, verification endpoint, and daily Merkle publication |
| 03 | [Verifiable credentials and KYC](./03-verifiable-credentials-kyc.md) | Issuer, wallet, selective disclosure, revocation, and policy proof inputs |
| 04 | [AI-resilient security and fraud](./04-ai-resilient-security-fraud.md) | LLM guards, output-term verification, red-team CI, and application fraud scoring |
| 05 | [Payments ledger](./05-payments-ledger.md) | Double-entry PostgreSQL ledger, idempotency, mandates, scheduler, and reconciliation |
| 06 | [Sovereign cloud mode](./06-sovereign-cloud-mode.md) | Provider abstraction, local inference, egress denial, region controls, and envelope encryption |
| 07 | [Trust dashboard](./07-trust-dashboard.md) | Admin view of trust signals with measurable metrics and alert states |
| 08 | [Signed sanction letters](./08-signed-sanction-letters.md) | Ed25519-signed PDF and public hash verification |

## Implementation plan

The detailed execution plan for the first four foundational workstreams is in
[TrustLend first-four implementation plan](../implementation/trustlend-first-four-plan.md).

## Delivery order

1. Establish [shared contracts](./00-shared-contracts.md) and complete
   [security remediation](./01-security-remediation.md).
2. Implement [audit chaining](./02-tamper-evident-audit.md), because every later
   module must emit verifiable events.
3. Implement [AI guards](./04-ai-resilient-security-fraud.md), then run the
   red-team suite before changing customer-facing prompts.
4. Implement [signed letters](./08-signed-sanction-letters.md) and use the audit
   verifier in the demo.
5. Add [verifiable KYC](./03-verifiable-credentials-kyc.md) and
   [sovereign mode](./06-sovereign-cloud-mode.md).
6. Add [payments](./05-payments-ledger.md) and finish the
   [trust dashboard](./07-trust-dashboard.md).

## Definition of done for the specification set

- Every module has an owner boundary and does not move lending decisions into the
  LLM.
- Every sensitive value has a storage, logging, and LLM handling rule.
- Every externally visible claim has a deterministic source or verification method.
- Every module has failure behavior and acceptance tests.
- Existing Aadhaar/PAN KYC remains available as an explicitly marked fallback until
  credential verification reaches parity.
