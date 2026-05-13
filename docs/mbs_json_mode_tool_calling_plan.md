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