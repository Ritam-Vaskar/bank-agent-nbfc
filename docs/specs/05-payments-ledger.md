# Payments ledger specification

## Goal

Replace `simulate_disbursement` with a transactional payment service backed by a
balanced PostgreSQL double-entry ledger. This is a prototype payment rail, not a
claim of live UPI settlement.

## Ledger model

Tables:

- `ledger_accounts(account_id, account_type, currency, status)`;
- `ledger_transactions(txn_id, idempotency_key, transaction_type, status, created_at)`;
- `ledger_entries(entry_id, txn_id, account_id, debit_paise, credit_paise)`;
- `payment_attempts(payment_id, txn_id, provider_ref, status, error_code)`;
- `outbox_events(outbox_id, event_type, aggregate_id, payload, published_at)`.

Constraints:

- exactly one of debit or credit is positive per entry;
- amounts are positive integers in paise;
- each transaction has at least two entries;
- a deferred constraint or transaction trigger enforces total debits equal total
  credits;
- `idempotency_key` is unique per operation scope.

## Disbursement

`POST /api/loans/{loan_id}/disburse` requires an idempotency key, authenticated
actor, accepted sanction, successful final checks, and a valid ledger account.
The service writes ledger entries and an outbox event in one database transaction.
Provider calls are retried through a payment-attempt state machine and never create
another ledger transaction for the same key.

## Collections

- Store a mock UPI AutoPay mandate with status, masked handle, consent timestamp,
  max debit, and expiry.
- An APScheduler or ARQ job creates due collection intents from the EMI schedule.
- A successful collection posts borrower debit and lender credit entries.
- A failed attempt remains visible with a retry policy and audit event.

## Reconciliation

A scheduled job compares active loan EMI schedules, payment attempts, and ledger
transactions. It emits drift records for missing, duplicate, overpaid, underpaid,
or misapplied entries. Drift blocks automatic closure and appears on the dashboard.

## Load test

Use k6 against disbursement or payment intent creation with documented dataset,
concurrency, VM size, database settings, TPS, p50, p95, p99, and error rate. Do not
publish a performance claim without the run artifact and test command.

## Acceptance criteria

- Pressing pay twice with the same key produces one financial effect.
- Every successful transaction balances exactly to zero.
- A database retry cannot duplicate disbursement or collection.
- Reconciliation detects a deliberately altered schedule or missing ledger entry.
- Performance reporting contains measured TPS and p95 latency.
