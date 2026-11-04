# Architecture

## Product model

CommitmentGraph stores four connected record classes:

- Commitments: obligations with counterparty, owner, status, due date, declared value and optional source record.
- Evidence: original uploaded file bytes, extracted text, media type, byte size and SHA-256 content digest. Original bytes remain downloadable for independent inspection.
- Events: dated changes or fulfilment events attached to a commitment, with an explicit approval flag and optional source record.
- Findings: deterministic rule-engine results, including rule code, severity, reasoning, lifecycle status and evidence IDs.

The relationship graph is derived from these records. It is not a separate source of truth.

## Processing path

1. An operator uploads a supported source file or imports a commitment CSV.
2. The parser preserves original bytes, extracts searchable text and computes a SHA-256 digest. Duplicate content is detected. Existing text-only records are migrated with an empty original-file field and remain explicitly marked as legacy.
3. The operator creates commitments and records events. Source IDs can be attached through the API.
4. The investigation engine evaluates explicit rules.
5. Findings are persisted and can be reviewed or resolved.
6. The register, findings and graph can be exported for independent examination.

## Rule catalogue

| Rule | Trigger | Severity |
|---|---|---|
| OVERDUE_COMMITMENT | Due date is before the investigation date and status is not fulfilled/cancelled | High |
| INVALID_DUE_DATE | Stored due date is not an ISO date | Low |
| UNAPPROVED_CHANGE | Scope-change, amendment or requirement-change event is not marked reviewed or has no linked source record | Critical |
| FULFILMENT_UNSUPPORTED | Commitment is marked fulfilled but no delivery/handover/completion/acceptance event has a linked source record | Medium |
| BILLING_REVIEW | Billing event exists and commitment has a declared value | Low |

Rules are intentionally conservative. Billing review does not extract or compare invoice amounts. An unapproved or unsubstantiated change is a review flag, not proof that approval was absent in the underlying business process. A delivery event without a linked source record does not count as evidence of fulfilment.

## Deployment

The supported deployment is a single Docker container with a persistent SQLite volume. Use a strong API key, TLS termination at a trusted reverse proxy, encrypted host storage, backups and a restricted operator network. SQLite is suitable for a single-instance deployment; move to a managed relational database before multi-instance or high-concurrency use.

## Extension boundaries

The v1 product does not claim automatic legal interpretation, semantic contract obligation extraction, ERP integration, e-signature validation, identity verification, or autonomous approval decisions. These require separate source-specific integrations and validation.
