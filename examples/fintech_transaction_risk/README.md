# Fintech Transaction Risk Workflow Pack

This is a serious workflow fixture for MBS structured-output reliability work. It models a payment-risk agent that must emit strict JSON for authorization, customer verification, manual-review routing, and audit records.

## What this tests

- Nested JSON schema validity.
- Transaction ID pattern enforcement.
- Strict enums for risk level, decision, signals, customer message, and audit channel.
- Numeric bounds for risk score and signal weights.
- Required nested signal evidence.
- `const` enforcement for `model_policy_version`.
- Extra-key rejection for debug and raw screening payload fields.
- Semantic correctness for risk level and decision.
- Prompt-injection resistance in transaction descriptions.

## Files

- `schema.json` — strict transaction-risk output schema.
- `cases.jsonl` — eight transaction cases with expected semantic outputs.
- `provider_good_responses.jsonl` — fixture responses expected to pass schema and semantic gates.
- `provider_bad_responses.jsonl` — fixture responses mixing semantic mistakes and schema violations.
- `policy.md` — operational policy used to guide provider collection prompts.
- `output.json` — one example valid output.

## Evidence boundary

These fixtures are software/regression evidence only. They are not broad model/provider benchmark evidence until populated with real provider responses and recorded as provider-classified evidence packs.
