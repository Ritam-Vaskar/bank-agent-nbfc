# Tamper-evident audit trail specification

## Goal

Turn the existing MongoDB `audit_logs` collection into an append-only, verifiable
event chain and publish an external daily commitment.

## Record contract

Each document contains the shared event envelope plus:

```json
{
  "sequence": 123,
  "prev_hash": "64-char hex SHA-256",
  "entry_hash": "64-char hex SHA-256",
  "hash_algorithm": "SHA-256",
  "canonicalization": "JCS-like sorted UTF-8 JSON v1",
  "chain_id": "trustlend-production",
  "committed_at": "UTC timestamp"
}
```

`entry_hash = SHA256(prev_hash || canonical_json(entry_without_entry_hash))`.
The first entry uses a fixed all-zero hash. Canonicalization must sort object keys,
use UTF-8, omit database-generated `_id`, and serialize numbers consistently.

## Write path

- Serialize writes through a repository-level atomic sequence allocator.
- A unique index covers `(chain_id, sequence)` and `entry_hash`.
- The writer reads the previous committed hash, builds the next record, and inserts
  it with a unique constraint.
- On conflict or unavailable audit storage, critical operations fail closed; no
  success response may be returned without the required event.
- No update or delete API exists for audit records. Administrative correction is a
  compensating event.

## Verification API

`GET /api/admin/audit-logs/verify?chain_id=...&from_sequence=...&to_sequence=...`

Response:

```json
{
  "valid": false,
  "chain_id": "trustlend-production",
  "checked": 241,
  "first_broken": {
    "sequence": 241,
    "log_id": "uuid",
    "reason": "entry_hash_mismatch|prev_hash_mismatch|sequence_gap|invalid_canonical_json"
  },
  "verified_at": "UTC timestamp"
}
```

The endpoint is admin-only, paginated, bounded, and itself emits an audit event.
An empty chain is valid only when explicitly requested for a new chain.

## Daily Merkle commitment

- At UTC day close, read the day’s ordered entry hashes and build a binary Merkle
  tree, duplicating the final node for odd levels.
- Write `{chain_id, date, first_sequence, last_sequence, merkle_root, algorithm}`
  to an object-lock-capable bucket or append-only signed file.
- Retain the publication URI and publication hash in a separate audit event.
- A verification job must compare the daily root with MongoDB and alert on mismatch.

## Acceptance criteria

- Editing any record causes verification to identify the first broken sequence.
- Removing or inserting a record causes a sequence-gap or previous-hash failure.
- Concurrent writers cannot create duplicate sequences or two valid successors.
- Re-running verification is deterministic.
- A daily root can be independently recomputed from exported records.
