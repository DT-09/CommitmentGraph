# Cloudflare Pages deployment

CommitmentGraph has two separate runtime parts:

1. **Public website and browser workspace** — static files in `static/`, deployed to Cloudflare Pages.
2. **Application API and database** — the FastAPI service, deployed separately with Docker. Cloudflare Pages Functions proxy `/api/*` to this service.

A Pages deployment alone does not run the Python API or create a persistent database.

## Pages project

Connect this repository to Cloudflare Pages and use:

- Production branch: `main`
- Build command: none
- Build output directory: `static`
- Root directory: repository root

The root `wrangler.toml` declares `pages_build_output_dir = "./static"`. The Pages Function under `functions/api/[[path]].js` is discovered from the repository root.

## Deploy the API

Deploy the FastAPI application using the repository's Dockerfile and persistent storage. Follow the Docker instructions in the README. Set these environment variables on the API service:

- `COMMITMENTGRAPH_API_KEY`: a long, unique secret.
- `DATA_DIR`: a persistent mounted directory, such as `/app/data`.

Use HTTPS for the public API origin. Keep the SQLite data volume persistent and backed up. Do not use ephemeral container storage for customer records.

## Connect Pages to the API

In Cloudflare Pages project settings, add the following variables for both production and preview environments as appropriate:

- `COMMITMENTGRAPH_API_ORIGIN`: the HTTPS origin of the FastAPI service, with no trailing slash or `/api` suffix.
- `COMMITMENTGRAPH_API_KEY`: the same secret configured on the API service. Store it as a secret, not a plain-text build variable.

The Pages Function injects this credential server-side. It does not forward browser cookies and does not expose the configured secret to client-side JavaScript.

After changing environment variables, trigger a new Pages deployment.

## Protect the workspace

**Do not expose a shared workspace containing business records to the public internet.** Version 1 has a single shared SQLite workspace; it does not provide customer tenancy, user accounts, or role-based access.

Before connecting a real database:

1. Configure Cloudflare Access (or an equivalent access gateway) to require authorised users for `/workspace*` and `/api/*`.
2. Restrict the API origin itself with its API key and, where practical, network or tunnel controls.
3. Use a dedicated deployment and database for each organisation.
4. Review `docs/security.md`, backup and retention requirements before uploading confidential records.

The public marketing page at `/` does not require API access. The workspace at `/workspace` reports API connectivity and remains unavailable until both Pages secrets and the backend are configured.

## Local development

The FastAPI application serves the marketing page at `/` and the operational workspace at `/workspace`. Run it using the local instructions in the README. In a direct FastAPI deployment, the browser can use the Settings screen to supply the API key. In the Pages deployment, the edge proxy injects the secret instead.
