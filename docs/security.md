# Security and operational controls

CommitmentGraph stores source documents and business records. Treat the database, backups, exports and API credentials as confidential business data.

## Included controls

- Optional shared API-key authentication for all application data endpoints.
- Constant-time API-key comparison.
- Parameterized SQLite queries and foreign-key enforcement.
- Baseline security headers on API responses and `Cache-Control: no-store` for API routes.
- Upload allowlist, 12 MB file limit and a 500-page PDF processing ceiling.
- Strict UTF-8 handling for text uploads and bounded text extraction.
- SHA-256 content hashing, duplicate detection and original-file integrity checks.
- Original uploaded bytes retained with extracted text for source re-download.
- Typed request validation for dates, currencies, statuses and event bundles.
- CSV import validation for schema, row count, dates, statuses, currencies and finite non-negative values.
- Spreadsheet-formula neutralization on CSV exports.
- Extracted text is returned as JSON and escaped by the browser UI.
- Container runs as a non-root user with dropped Linux capabilities.
- Persistent data is isolated in a Docker volume.
- Cloudflare Pages proxy injects its server-side API key and does not forward browser cookies.

## Required before production use

1. Set a unique, high-entropy `COMMITMENTGRAPH_API_KEY` on the API service and the matching secret on the Pages project. Never use the example value.
2. Put the service behind HTTPS. Do not expose port 8000 directly to the public internet.
3. Restrict workspace access to named operators through an identity-aware access gateway.
4. Use a dedicated deployment and database per customer. The current product is a single shared workspace, not a multi-tenant SaaS service.
5. Encrypt the host volume and backups at rest.
6. Define retention, deletion and incident-response procedures for source documents.
7. Back up the SQLite database and test restoration before relying on it.
8. Review uploaded records for confidential, personal, export-controlled or regulated content.
9. Rotate the API key after staff changes or suspected disclosure.
10. Keep dependencies and the container base image patched; review CI results before release.

## Authentication limits

When `COMMITMENTGRAPH_API_KEY` is unset, the API intentionally permits unauthenticated access for local development. This is not safe for a public deployment. A shared API key is a deployment gate, not individual identity, role-based access control, tenant isolation or an audit trail of who performed an action. The browser stores the entered key in local storage. Use a private, managed workstation and an access gateway for production.

## Evidence and analysis limits

A SHA-256 digest identifies the exact uploaded bytes. It does not establish authenticity, authorship, signature validity, timestamp accuracy or legal chain of custody. OCR is not included; image-only PDFs may have no extractable text. Older records created before original-file retention remain text-only.

Investigation findings are deterministic review signals based on structured records. They are not legal advice, proof of fraud, proof of approval or a substitute for professional contract, accounting or compliance review. Operators must inspect the original source records and document their decisions.
