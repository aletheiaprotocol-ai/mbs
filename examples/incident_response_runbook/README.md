# Incident Response Runbook Workflow Pack

This is a serious workflow fixture for MBS structured-output reliability work. It models an incident-response agent that must emit strict JSON for automation, paging, remediation, and customer communication.

## What this tests

- Nested JSON schema validity.
- Strict enum adherence for severity, owner, operation, and channel.
- Required nested action objects.
- Numeric bounds for confidence and deadlines.
- `const` enforcement for `runbook_version`.
- Extra-key rejection for unsafe/debug fields.
- Semantic correctness against incident severity and incident ID expectations.
- Prompt-injection resistance in incident text.

## Files

- `schema.json` — strict incident response output schema.
- `cases.jsonl` — eight incident cases with expected semantic outputs.
- `provider_good_responses.jsonl` — fixture responses expected to pass schema and semantic gates.
- `provider_bad_responses.jsonl` — fixture responses mixing semantic mistakes and schema violations.
- `policy.md` — operational policy used to guide provider collection prompts.

## Evidence boundary

These fixtures are software/regression evidence only. They are not broad model/provider benchmark evidence until populated with real provider responses and recorded as provider-classified evidence packs.
