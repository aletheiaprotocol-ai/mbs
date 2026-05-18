# Support Ticket Triage Workflow

This example exercises MBS on a realistic customer-support triage workflow.

It validates that an agent can emit strict structured output for:

- security/account takeover escalation,
- billing review,
- engineering incident escalation,
- self-service how-to routing,
- privacy/GDPR handling,
- production outage triage,
- feature request capture,
- phishing suspicion handling.

## Files

- `schema.json` — strict nested JSON schema with enums, bounds, arrays, nested objects, and `additionalProperties: false`.
- `cases.jsonl` — eight semantic cases with top-level expected outputs.
- `provider_good_responses.jsonl` — fixture responses that should pass schema and semantic checks.
- `provider_bad_responses.jsonl` — fixture responses covering semantic mismatch, invented enum, wrong type, extra key, bounds, too-few-items, missing nested key, and const mismatch.
- `policy.md` — routing and safety policy.
- `output.json` — one valid sample output.

## Evidence boundary

This pack is software/regression evidence only. It proves the MBS adapter, validation, gate, reporting, and evidence-pack path can handle this workflow shape. It is not broad model/provider benchmark evidence and must not be used as an enterprise production readiness claim.
