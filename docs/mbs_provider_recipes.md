# MBS Provider Recipes

This guide shows how to turn real provider responses into MBS evidence packs.

Use it for agent outputs from text completion, JSON mode, or tool/function
calling. The examples use local fixtures so the flow is copy/pasteable without a
provider key. Replace the fixture JSONL with rows from your provider SDK.

Local fixture commands use `benchmarks/fixture_smoke_gate.yaml`, which is a
small software-check gate. Real provider runs should use a copied/tuned version
of `benchmarks/provider_gate.example.yaml`.

## Evidence Boundary

Provider recipes are not benchmark claims by themselves. A provider evidence
pack is model-behavior evidence only for the listed schema, cases, model,
decoding mode, retry policy, temperature, seed, and run settings.

Keep these separate:

- `fixture` classification: local smoke fixture, not provider benchmark evidence;
- `provider` classification: real provider outputs collected from an API run;
- `oss` or `hpc` classification: local/open model outputs from controlled runs.

## Response JSONL Shape

Each line should identify the case and include one provider output:

```json
{"case_id":"tool_001","output":{"tool":"escalate_case","priority":"HIGH","reason":"..."}}
```

Supported output fields:

- `output`
- `response`
- `content`
- `arguments`
- `tool_arguments`
- `tool_call.function.arguments`
- first item in `tool_calls[].function.arguments`

Optional fields that MBS preserves or uses:

- `model`
- `prompt_style`
- `decoding_mode`
- `language`
- `tokens`
- `latency_s`
- `provider_error` / `api_error` / `infra_failure`

## 1. Text-Mode Recipe

Text-mode rows are useful because they catch a common failure: the model explains
what it would do instead of returning the exact structured object.

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses examples/tool_argument_generation/provider_text_responses.jsonl \
  --model fixture-provider-text \
  --decoding-mode text \
  --out benchmarks/results/provider_text_fixture.mbs.json

mbs evidence-pack \
  --results benchmarks/results/provider_text_fixture.mbs.json \
  --classification fixture \
  --allow-missing-traces \
  --copy-results \
  --out-dir benchmarks/results/evidence_pack_text_fixture
```

Expected fixture behavior: the fixture includes one prose response and one
structured response. It is a smoke check that proves failures are surfaced, not
real provider evidence.

## 2. JSON-Mode Recipe

JSON-mode rows should contain a parsed JSON object in `output`, `arguments`, or
`tool_arguments`.

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses examples/tool_argument_generation/provider_json_mode_responses.jsonl \
  --model fixture-provider-json-mode \
  --decoding-mode json_mode \
  --out benchmarks/results/provider_json_mode_fixture.mbs.json

mbs gate \
  --results benchmarks/results/provider_json_mode_fixture.mbs.json \
  --config benchmarks/fixture_smoke_gate.yaml \
  --out benchmarks/results/provider_json_mode_gate.json

mbs evidence-pack \
  --results benchmarks/results/provider_json_mode_fixture.mbs.json \
  --gate-config benchmarks/fixture_smoke_gate.yaml \
  --classification fixture \
  --copy-results \
  --out-dir benchmarks/results/evidence_pack_json_mode_fixture
```

For a real provider run, change `--classification fixture` to
`--classification provider`, change the gate to a copied/tuned version of
`benchmarks/provider_gate.example.yaml`, and record the model/deployment,
temperature, seed, and prompt contract used to collect the JSONL.

## 3. Tool-Call Recipe

Tool/function-call rows should preserve the provider's nested tool-call shape.
MBS extracts `function.arguments` and validates that object against the schema.

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses examples/tool_argument_generation/provider_tool_call_responses.jsonl \
  --model fixture-provider-tool-call \
  --decoding-mode tool_call \
  --out benchmarks/results/provider_tool_call_fixture.mbs.json

mbs gate \
  --results benchmarks/results/provider_tool_call_fixture.mbs.json \
  --config benchmarks/fixture_smoke_gate.yaml \
  --out benchmarks/results/provider_tool_call_gate.json

mbs evidence-pack \
  --results benchmarks/results/provider_tool_call_fixture.mbs.json \
  --gate-config benchmarks/fixture_smoke_gate.yaml \
  --classification fixture \
  --copy-results \
  --out-dir benchmarks/results/evidence_pack_tool_call_fixture
```

## 4. Compare Text vs JSON Mode vs Tool Calls

After adapting each mode, compare controlled runs. Keep one variable different
at a time.

```bash
mbs compare \
  --baseline benchmarks/results/provider_text_fixture.mbs.json \
  --current benchmarks/results/provider_json_mode_fixture.mbs.json \
  --match-on schema,language \
  --out benchmarks/results/compare_text_vs_json_mode.json

mbs compare \
  --baseline benchmarks/results/provider_json_mode_fixture.mbs.json \
  --current benchmarks/results/provider_tool_call_fixture.mbs.json \
  --match-on schema,language \
  --out benchmarks/results/compare_json_mode_vs_tool_call.json
```

If you reuse the same `--model` value for all modes, you may match on
`schema,model,language`. If no rows match, MBS returns `NO_MATCH` instead of
pretending the comparison passed.

## 5. Provider Gate Checklist

Before calling a run provider evidence, verify:

1. raw provider JSONL is kept;
2. case IDs map to fixed cases;
3. model/deployment and decoding mode are recorded;
4. temperature, seed, retry policy, and tool/function schema are documented;
5. `mbs report --require-traces` passes;
6. `mbs gate --config benchmarks/provider_gate.example.yaml` passes or the failure is explained;
7. `mbs triage` exports concrete failure examples;
8. `mbs evidence-pack --classification provider --copy-results` produces the review bundle.

## 6. CI Pattern For Real Provider Outputs

Do not put provider keys in this repo. Collect provider JSONL in your own secure
job, then run MBS on the saved response file:

```bash
mbs adapt-responses --schema path/to/schema.json --cases path/to/cases.jsonl --responses provider_responses.jsonl --model provider-model --decoding-mode tool_call --out results/provider_tool_call.mbs.json
mbs report --results results/provider_tool_call.mbs.json --exclude-infra --require-traces --summary-only --out results/provider_report.md
mbs gate --results results/provider_tool_call.mbs.json --config benchmarks/provider_gate.example.yaml --out results/provider_gate.json
mbs triage --results results/provider_tool_call.mbs.json --out results/provider_triage.json
mbs evidence-pack --results results/provider_tool_call.mbs.json --gate-config benchmarks/provider_gate.example.yaml --classification provider --copy-results --out-dir results/evidence_pack_provider
```
