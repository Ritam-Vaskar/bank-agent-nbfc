# Trust dashboard specification

## Goal

Add one admin view that exposes the health of TrustLend controls without exposing
customer PII or pretending that an unavailable signal is healthy.

## Metrics

Required cards and drill-downs:

- audit chain: valid/broken, last verified sequence, last daily root;
- blocked injection attempts over time;
- output-guard mismatches and fallback-template count;
- fraud flags by reason and status;
- ledger balance check and unreconciled drift;
- credential verification success, expiry, and revocation failures;
- sovereign mode, selected provider, region, and last egress policy check;
- authentication failures and cookie migration status.

Metrics labels must use bounded enumerations and hashes/IDs, never email, PAN,
Aadhaar, prompt text, IP addresses, or free-form user content.

## API

Admin-only endpoints return current status plus `observed_at`, `source`, and
`stale_after`. If a source is unavailable, the response is `unknown` with an error
code, not green.

Suggested endpoints:

- `GET /api/admin/trust/summary`
- `GET /api/admin/trust/audit`
- `GET /api/admin/trust/ai`
- `GET /api/admin/trust/fraud`
- `GET /api/admin/trust/ledger`
- `GET /api/admin/trust/residency`

## Observability

Use existing structured logging and add Prometheus/OpenTelemetry instrumentation at
guard, verifier, ledger, egress, and audit boundaries. Trace IDs may link events,
but traces must obey the shared privacy classes.

## Acceptance criteria

- An admin sees all required signals in one page.
- Deliberately breaking an audit record, mismatching an offer, blocking egress, and
  creating ledger drift change the corresponding cards.
- A datastore outage is shown as unknown/stale and raises an operational alert.
- A normal user cannot access dashboard APIs or infer another user's data.
