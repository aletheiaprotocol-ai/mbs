# Security Policy

## Supported scope

This repository is currently an early-stage developer tool for structured-agent-output validation. Security support applies to the latest code on the main development branch and the most recent tagged release.

## Reporting a vulnerability

Do not file public issues with exploitable details or credentials. Report suspected vulnerabilities privately to the maintainers by email at `aletheia@fenicebrand.com` with:

- affected command, API, script, or workflow;
- reproduction steps using sanitized inputs;
- expected impact;
- whether any credential, customer data, or provider artifact was exposed.

The maintainer target is to acknowledge actionable reports within 7 days.

## Secrets and credentials

MBS must not require hardcoded provider secrets. Provider scripts read credentials from environment variables supplied by the operator, for example `AZURE_OPENAI_API_KEY`, `OPENAI_API_KEY`, or a custom `--api-key-env` value.

Do not commit:

- API keys, access tokens, refresh tokens, or SSH keys;
- raw customer data;
- proprietary provider outputs unless explicitly sanitized;
- generated virtual environments or local cache folders.

## Data and artifact handling

MBS traces include schema, contract, input, and output hashes plus validation metadata. They are designed for auditability, not as a privacy boundary. Treat raw inputs, raw outputs, benchmark rows, evidence packs, and provider response files as potentially sensitive until reviewed and classified.

## Current release boundary

MBS is not marked Enterprise Pilot Ready until the release/security hygiene checklist, provider-classified evidence, CI matrix, and cross-platform install proof are complete.