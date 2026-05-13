# JSON-Mode and Tool-Calling Adapter Plan

MBS currently measures structured outputs after a model or agent runtime returns
text/JSON. The next adapter layer should let teams evaluate native provider JSON
mode and tool-calling outputs with the same MBS result schema.

## Goal

Make provider-specific structured-output modes comparable without turning MBS
into a model gateway.

MBS should answer:

- Did native JSON mode improve clean JSON rate?
- Did tool calling improve schema validity?
- Did either mode hurt semantic correctness?
- Did retry improve the selected output or only add cost?
- Which failures are model behavior, adapter behavior, or infrastructure?

## Non-Goals

- MBS will not store API keys.
- MBS will not proxy production traffic.
- MBS will not claim provider parity from one model or one schema.
- MBS will not treat valid JSON as success when the semantic decision is wrong.

## Adapter Contract

Each adapter should produce ordinary MBS benchmark rows with these fields:

- `schema`
- `case_id`
- `model`
- `prompt_style`
- `decoding_mode`
- `language`
- `output`
- `validation`
- `trace`
- `tokens`
- `cost`
- `attempts` when retry is enabled

Suggested `decoding_mode` values:

- `text`
- `json_mode`
- `tool_call`
- `tool_call_strict`

## Adapter Interface

Adapters should be thin wrappers around a user-owned model call:

```python
def run_case(case: dict, schema: dict, contract: str) -> dict:
    """Return an MBS-compatible row for one case."""
```

The wrapper is responsible for provider I/O. MBS remains responsible for:

1. compiling the schema into a behavioral contract;
2. validating returned arguments/output;
3. classifying format/schema/semantic failures;
4. creating traces;
5. reporting cost per valid output;
6. comparing modes and retry policies.

## Minimum Evaluation Matrix

For each provider/runtime adapter:

| dimension | minimum |
| --- | --- |
| schemas | 2 hard structured-output schemas |
| cases | at least 5 per schema |
| modes | `text`, `json_mode` or `tool_call` |
| retry | no retry and one MBS retry |
| seeds | deterministic first; sampled later |
| required reports | aggregate report, compare report, retry audit, triage examples |

## Comparison Rules

Use strict row identity by default:

```bash
mbs compare \
  --baseline results/text_mode.json \
  --current results/json_mode.json \
  --match-on schema,model,prompt_style,decoding_mode,language
```

## Reproducible Adapter Smoke Pipeline

The repository includes tiny provider-response fixtures for the tool-argument
example:

- `examples/tool_argument_generation/provider_text_responses.jsonl`
- `examples/tool_argument_generation/provider_tool_call_responses.jsonl`

Run the smoke pipeline:

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

mbs report --results results/tool_call_fixture.mbs.json --require-traces --summary-only

mbs compare \
  --baseline results/text_fixture.mbs.json \
  --current results/tool_call_fixture.mbs.json \
  --match-on schema,model,language
```

This proves only that the adapter, report, and compare pipeline works on fixture
data. It is a smoke test, not benchmark evidence for any provider or model.

For controlled mode ablations, compare on shared identity fields and keep the
changed field explicit in the report:

```bash
mbs compare \
  --baseline results/text_mode.json \
  --current results/tool_call.json \
  --match-on schema,model,language
```

An empty comparison must be treated as `NO_MATCH`, not as a pass.

## Evidence Standard

An adapter result is credible only when it includes:

- raw result JSON files;
- trace coverage;
- infrastructure failures separated from behavior rows;
- failure examples;
- cost per valid output;
- retry improvements and retry regressions;
- explicit statement of what the benchmark does not prove.

## First Implementation Step

Add one local adapter that accepts a JSONL file of provider responses and emits
MBS benchmark rows. This avoids committing to any provider SDK while proving the
adapter contract and report format.

Implemented command:

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses results/provider_responses.jsonl \
  --model provider-model-name \
  --decoding-mode json_mode \
  --out results/provider_responses.mbs.json
```

Accepted JSONL row shape:

```json
{"case_id":"case-1","input":"...","output":{"tool":"search_customer","arguments":{"customer_id":"123"}},"expected_valid_outputs":{"tool":"search_customer"},"tokens":{"output":42}}
```

The adapter also accepts provider-style output fields named `response`,
`content`, `arguments`, `tool_arguments`, `tool_call.arguments`, or
`tool_call.function.arguments`. If `--cases` is supplied, cases are merged by
`case_id`/`id` and then row order so semantic expectations can live in the
original benchmark file. It emits normal MBS result JSON, so the existing report,
compare, retry-audit, and triage commands work unchanged:

```bash
mbs report --results results/provider_responses.mbs.json --require-traces --summary-only
mbs compare --baseline results/text_mode.mbs.json --current results/provider_responses.mbs.json --match-on schema,model,language
```