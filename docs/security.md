# Security and operational controls

## Included controls

- Optional API-key authentication for all application data endpoints.
- Constant-time API-key comparison.
- No user account system or third-party analytics.
- Parameterized SQLite queries.
- Upload allowlist and 12 MB per-file limit.
- SHA-256 content hashing and duplicate detection.
- Extracted text is served as JSON and escaped by the browser UI.
- Container runs as a non-root user with dropped Linux capabilities.
- Persistent data is isolated in a Docker volume.

## Required before production use

1. Set a unique, high-entropy COMMITMENTGRAPH_API_KEY; never use the example value.
2. Put the service behind HTTPS. Do not expose port 8000 directly to the public internet.
3. Restrict network access to named operators or a trusted identity-aware proxy.
4. Encrypt the host volume and backups at rest.
5. Define retention and deletion rules for source documents.
6. Back up the SQLite database and test restoration.
7. Review uploaded records for confidential, personal, export-controlled or regulated content.
8. Rotate the API key after staff changes or suspected disclosure.

## Known limitations

The application stores extracted text rather than original file binaries. A file's SHA-256 digest identifies the uploaded bytes but does not establish authenticity, authorship, signature validity or chain of custody. API-key authentication is a shared-secret gate, not individual identity or role-based access control. The browser stores the entered key in local storage. Use a private, managed workstation.

Do not use findings as legal advice, proof of fraud, or a substitute for professional contract, accounting or compliance review.
