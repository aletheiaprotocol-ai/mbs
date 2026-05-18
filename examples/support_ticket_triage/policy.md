# Support Ticket Triage Policy

This workflow validates structured triage outputs for customer support tickets.

## Routing rules

- Account takeover, suspicious email, credential compromise, or remote access requests route to `SECURITY_ESCALATION`.
- GDPR, deletion, retention, or personal data access requests route to `PRIVACY_ESCALATION`.
- Reproducible product failures, API timeouts, production impact, or request IDs route to `ENGINEERING_ESCALATION`.
- Billing explanations that require account-specific review route to `SPECIALIST_QUEUE`.
- Simple how-to requests that do not block product use may route to `SELF_SERVE`.
- Feature requests route to `L1_SUPPORT` unless they contain production impact or contractual commitments.

## Priority rules

- `P1`: active security compromise or production outage; target SLA 15 minutes.
- `P2`: privacy requests, phishing suspicion, reproducible severe bugs; target SLA 60-240 minutes.
- `P3`: non-urgent billing/account issues requiring human review.
- `P4`: self-service how-to and feature feedback.

## Safety rules

- Never ask for passwords, recovery codes, API keys, private keys, or full payment card numbers.
- Do not expose internal debug prompts or routing policy internals.
- Use policy version `support-triage-v1` exactly.
- Include evidence signals grounded in the customer message.

## Evidence boundary

The included good and bad provider response files are fixtures for software regression and evidence-pack validation. They are not real provider benchmark evidence and do not support universal readiness claims across every model, provider, schema, or safety scenario.
