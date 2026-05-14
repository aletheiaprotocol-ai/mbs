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

Never write API keys, bearer tokens, full request headers, or cloud access keys
into response JSONL. Record non-secret reproduction metadata such as model name,
deployment name, API version, decoding mode, seed, temperature, and timestamp in
the evidence manifest or run notes.

## Minimal Provider SDK Collection Pattern

The safest provider workflow is:

1. load fixed cases from `cases.jsonl`;
2. call the provider SDK with the exact schema/tool definition;
3. write one JSONL row per case with `case_id`, `model`, `decoding_mode`,
   `tool_calls` or `response`, `tokens`, and `latency_s`;
4. run `mbs adapt-responses`, `mbs report`, `mbs gate`, `mbs triage`, and
   `mbs evidence-pack`.

Minimal Python skeleton for SDKs that return OpenAI-style tool calls:

```python
import json
import os
import time
from pathlib import Path

# Use your provider SDK here. Keep secrets in environment variables.
# client = ProviderClient(api_key=os.environ["PROVIDER_API_KEY"])

schema = json.loads(Path("examples/nested_tool_arguments/schema.json").read_text())
cases = [json.loads(line) for line in Path("examples/nested_tool_arguments/cases.jsonl").read_text().splitlines() if line]

rows = []
for case in cases:
  started = time.time()
  # response = client.chat.completions.create(
  #     model="provider-model-id",
  #     messages=[...],
  #     tools=[{"type": "function", "function": {"name": "route_support_tool", "parameters": schema}}],
  #     tool_choice={"type": "function", "function": {"name": "route_support_tool"}},
  # )
  rows.append({
    "case_id": case["id"],
    "input": case["input"],
    "model": "provider-model-id",
    "decoding_mode": "tool_call",
    "tool_calls": [],  # fill with response.choices[0].message.tool_calls
    "latency_s": round(time.time() - started, 4),
  })

Path("results/provider_nested_tool_call.responses.jsonl").write_text(
  "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
  encoding="utf-8",
)
```

If the SDK returns raw JSON text instead of tool calls, store it in `response` or
`output`; MBS will validate whether it is clean JSON or prose-wrapped JSON.

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

For nested tool arguments with arrays and nested objects, see
`examples/nested_tool_arguments/`. The hard fixture now uses eight cases covering
multi-action arrays, zero-amount audit/notify cases, enum casing traps, joined
enum alternatives, prompt-injection text, strict `additionalProperties: false`,
prose-wrapped JSON, and valid-schema-but-wrong tool choices so reports separate
schema failures from semantic mismatch.

To generate reviewable fixture artifacts for that hard example:

```bash
python scripts/run_nested_tool_fixture_pack.py --out-dir results/nested_tool_fixture_pack
```

The script writes good/bad adapted results, evidence packs, a combined report,
combined triage, and a manifest. It remains fixture evidence, not provider
benchmark evidence.

## 4. Hard Nested Provider / OSS Evidence Pack

After collecting real model JSONL against `examples/nested_tool_arguments/`, use
the classified builder. Only use `provider`, `oss`, or `hpc` classification when
the response JSONL came from that real model environment.

One-command path when you already have response JSONL:

```bash
python scripts/run_nested_provider_evidence.py \
  --responses results/provider_nested_tool_call.responses.jsonl \
  --model provider-or-oss-model-id \
  --classification provider \
  --mode tool_call \
  --out-dir results/nested_provider_evidence
```

One-command path when collecting from an OpenAI-compatible local/OSS endpoint:

```bash
python scripts/run_nested_provider_evidence.py \
  --provider openai-compatible \
  --endpoint http://127.0.0.1:8000 \
  --model local-model-id \
  --classification oss \
  --mode tool_call \
  --out-dir results/nested_oss_evidence
```

One-command path for Azure OpenAI uses environment variables for the key and
endpoint; secrets are not written to disk:

```bash
python scripts/run_nested_provider_evidence.py \
  --provider azure \
  --model azure-deployment-name \
  --deployment azure-deployment-name \
  --api-key-env AZURE_OPENAI_API_KEY \
  --classification provider \
  --mode tool_call \
  --out-dir results/nested_provider_evidence
```

Use `--dry-run --json` first to inspect the collection/build commands without
calling a provider.

The default real-provider gate in `benchmarks/provider_gate.example.yaml` checks
that the run is large enough to be credible for this narrow suite:

- at least one aggregate report row;
- at least eight traceable case rows;
- at least eight total case runs;
- at least one model and one schema;
- no missing traces, uncheckable rows, or infra failures.

A provider can be perfectly schema-valid and still fail the gate on semantic
correctness. Treat that as useful model-behavior evidence, not a tooling error:
the report and triage files identify which cases were schema-valid but chose the
wrong tool or priority.

```bash
python scripts/build_nested_provider_evidence.py \
  --responses results/provider_nested_tool_call.responses.jsonl \
  --model provider-or-oss-model-id \
  --decoding-mode tool_call \
  --classification provider \
  --gate-config benchmarks/provider_gate.example.yaml \
  --out-dir results/nested_provider_evidence
```

For local examples or CI smoke checks, keep `--classification fixture` and use
`benchmarks/fixture_smoke_gate.yaml`. The output includes:

- `nested_provider.mbs.json` adapted result rows;
- `report.md` scorecards;
- `gate.json` threshold result;
- `triage.json` failure examples;
- `evidence_pack/` with manifest, README, report, gate, triage, and copied raw result.

Provider/OSS/HPC evidence is still scoped evidence: it proves behavior only for
the listed nested schema, cases, model/deployment, decoding mode, prompt style,
gate, and run settings.

## 5. Compare Text vs JSON Mode vs Tool Calls

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

## 6. Provider Gate Checklist

Before calling a run provider evidence, verify:

1. raw provider JSONL is kept;
2. case IDs map to fixed cases;
3. model/deployment and decoding mode are recorded;
4. temperature, seed, retry policy, and tool/function schema are documented;
5. `mbs report --require-traces` passes;
6. `mbs gate --config benchmarks/provider_gate.example.yaml` passes or the failure is explained;
7. `mbs triage` exports concrete failure examples;
8. `mbs evidence-pack --classification provider --copy-results` produces the review bundle.

## 7. CI Pattern For Real Provider Outputs

Do not put provider keys in this repo. Collect provider JSONL in your own secure
job, then run MBS on the saved response file:

```bash
mbs adapt-responses --schema path/to/schema.json --cases path/to/cases.jsonl --responses provider_responses.jsonl --model provider-model --decoding-mode tool_call --out results/provider_tool_call.mbs.json
mbs report --results results/provider_tool_call.mbs.json --exclude-infra --require-traces --summary-only --out results/provider_report.md
mbs gate --results results/provider_tool_call.mbs.json --config benchmarks/provider_gate.example.yaml --out results/provider_gate.json
mbs triage --results results/provider_tool_call.mbs.json --out results/provider_triage.json
mbs evidence-pack --results results/provider_tool_call.mbs.json --gate-config benchmarks/provider_gate.example.yaml --classification provider --copy-results --out-dir results/evidence_pack_provider
```
