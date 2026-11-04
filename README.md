# CommitmentGraph

**Evidence-led commitment intelligence.** Reconstruct what a business promised, what changed, what was delivered, and what the available records support.

CommitmentGraph is a self-hosted operational investigation workspace for project-based businesses, engineering firms and industrial suppliers. It links obligations, dated events, source records and review findings into one inspectable relationship graph.

## What the product does

- Maintain a structured register of business commitments.
- Upload source records in PDF, DOCX, TXT, MD, CSV, JSON and LOG formats.
- Preserve the original uploaded file, extract searchable text and compute SHA-256 content digests.
- Download the original source file from its evidence record for independent inspection.
- Import commitment registers from CSV.
- Record amendments, scope changes, delivery, handover, acceptance and billing events.
- Link source evidence to commitments and events.
- Run deterministic investigations for overdue obligations, unapproved changes, unsupported fulfilment and billing review.
- Inspect the reasoning behind every finding.
- Explore a relationship graph connecting commitments, events, findings and source records.
- Export commitment and finding registers as CSV.

## What it does not claim

Version 1 does not autonomously interpret contract clauses, establish legal approval, prove fraud, verify digital signatures, reconcile invoice line items, or connect to ERP systems. Findings are review signals generated from structured records. Operators remain responsible for source interpretation and decisions.

## Run locally

Requirements: Python 3.11+.

    python -m venv .venv
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    pip install -e ".[dev]"
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000. With no API key configured, the local development server does not require authentication.

## Deploy with Docker

    cp .env.example .env

Replace the example API key with a unique secret, then:

    docker compose up --build -d

Open http://localhost:8000 and enter the same API key in Settings. Docker Compose persists records in the commitmentgraph_data volume.

For public deployment, put the service behind HTTPS and restrict access. Review docs/security.md before uploading business records.

## First use

1. Upload contracts, quotations, amendments, delivery records or other source documents.
2. Create commitments and specify the obligation, counterparty, owner, due date and declared value.
3. Record dated events and link the source record that supports each event.
4. Run an investigation.
5. Review each finding and inspect the linked evidence.
6. Export the register and findings for a separate human review.

A sample CSV is available at sample-data/commitments.csv.

## CSV schema

Required column: title.

Optional columns: counterparty, description, owner, status, due_date (ISO YYYY-MM-DD), value, currency.

## API

Interactive API reference: /api/docs.

Key endpoints:

- GET /api/health
- GET /api/overview
- GET and POST /api/commitments
- GET /api/commitments/{id}
- POST /api/commitments/{id}/events
- POST /api/evidence
- POST /api/import/csv
- POST /api/investigate
- GET /api/findings
- GET /api/graph
- GET /api/reports/commitments.csv
- GET /api/reports/findings.csv

When COMMITMENTGRAPH_API_KEY is set, send it in the x-api-key header.

## Engineering

    pip install -e ".[dev]"
    pytest

See docs/architecture.md and docs/security.md.

## Licence

No licence has been granted yet. All rights remain with the repository owner unless a licence is added.
