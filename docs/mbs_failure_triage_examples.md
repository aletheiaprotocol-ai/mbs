# MBS Failure Triage Examples

MBS is useful because it separates syntax, schema, semantic, and infrastructure failures. This page shows how to read common failures without overclaiming model reliability.

## Run Triage

```bash
mbs triage --results benchmarks/results/*.json --max-failure-examples 40 --out benchmarks/results/triage_failure_examples.json
```

For provider-response files:

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses provider_responses.jsonl \
  --model provider-model \
  --decoding-mode tool_call \
  --out provider_responses.mbs.json

mbs triage --results provider_responses.mbs.json --max-failure-examples 20
```

## Failure Classes

| failure | What it means | Usually indicates | Buyer-safe claim |
| --- | --- | --- | --- |
| `invalid_json` | Output cannot be parsed as JSON | Format failure or prose answer | MBS caught a non-structured response |
| `reasoning_prose` | Model returned reasoning/prose instead of raw JSON | Prompt/model behavior | MBS can distinguish explanation from structured output |
| `prose_wrapped_json` | JSON was wrapped in extra text | Format contamination | MBS can measure clean-JSON risk |
| `missing_required_key` | Required schema field absent | Schema-following failure | MBS catches incomplete tool arguments |
| `wrong_type` | Field has wrong JSON type | Schema-following failure | MBS catches type-unsafe arguments |
| `invalid_enum` | Field value is not one of the allowed enum values | Enum control failure | MBS catches unsupported actions/categories |
| `invented_enum` | Model invented a plausible but unsupported enum | Hallucinated structured decision | MBS catches fake-but-plausible actions |
| `semantic_mismatch` | JSON is valid but business/tool decision is wrong | Model behavior failure | MBS goes beyond JSON validation |
| `incomplete_traces` | Rows lack trace ids/tokens | Evidence pipeline failure | Result is not auditable enough yet |
| `missing_model_result` | Expected model has no result file | Benchmark coverage failure | Do not compare incomplete suites |

## How To Interpret A Result

A passing report means the checked rows met the configured thresholds. It does not prove universal reliability.

A failing report can still be valuable if it has:

- traceable case rows;
- clear failure examples;
- separated infrastructure failures;
- cost per valid output;
- comparable baseline/current files.

## Triage Checklist

1. **Check trace coverage first**: if traces are missing, fix the evidence pipeline before discussing model behavior.
2. **Separate infrastructure from behavior**: API failures, timeouts, or empty result files are not model failures.
3. **Inspect failure types**: invalid JSON and prose are format failures; enum/type/missing-key issues are schema failures; semantic mismatches are decision failures.
4. **Use compare for regressions**: do not eyeball two reports. Use `mbs compare` with explicit `--match-on` fields.
5. **Do not overclaim**: small fixtures are smoke tests. Real evidence needs hard cases, multiple schemas, traces, and repeated runs.

## Example: Tool-Call Smoke Fixture

The public fixture intentionally includes a weak text response and a clean tool-call response:

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses examples/tool_argument_generation/provider_text_responses.jsonl \
  --model fixture-provider \
  --decoding-mode text \
  --out results/text_fixture.mbs.json

mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses examples/tool_argument_generation/provider_tool_call_responses.jsonl \
  --model fixture-provider \
  --decoding-mode tool_call \
  --out results/tool_call_fixture.mbs.json

mbs compare \
  --baseline results/text_fixture.mbs.json \
  --current results/tool_call_fixture.mbs.json \
  --match-on schema,model,language
```

This is a smoke test. It proves the adapter/report/compare path works; it does not prove a provider is better.
