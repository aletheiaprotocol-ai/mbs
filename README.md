# MBS

MBS makes structured agent behavior measurable.

It compiles schemas into behavioral contracts, validates structured outputs,
creates portable traces, reports cost per valid output, and provides a starter
benchmark/test surface for structured-output reliability.

## Install

```bash
git clone https://github.com/aletheiaprotocol-ai/mbs.git
cd mbs
python -m pip install -e .
```

## 30-Second Demo

```bash
mbs demo
```

The demo shows one end-to-end flow:

- input schema + prompt
- minimal behavioral contract
- model output
- PASS / FAIL / REVIEW validation
- exact failure reason
- trace id
- retry repair
- token/cost comparison

To regenerate the demo artifacts:

```bash
mbs demo --write-artifacts
```

This writes:

- `benchmarks/results/sample_benchmark.json`
- `benchmarks/results/sample_benchmark.md`
- `docs/mbs_evidence_brief.md`

## What MBS Does

MBS is for teams building agents that must produce structured outputs before
they call tools, update records, or trigger workflows.

For each structured output, MBS provides:

- a behavioral contract from a schema
- PASS / FAIL / REVIEW validation
- exact failure reasons such as `invalid_enum`, `missing_required_key`, and `wrong_type`
- a trace id with schema, contract, input, and output hashes
- retry and cost-per-valid-output accounting
- strict JSON-only diagnostics for models that wrap JSON in prose or emit reasoning text instead of JSON

## Benchmark Sample

Deterministic local sample: 3 support-agent cases x 2 mock model adapters.

| strategy | cases | models | schema-valid | semantic-correct | avg retries | cost / valid output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| verbose prompt | 6 | 2 | 0.500 | 0.500 | 0.000 | 385.0 |
| MBS contract + retry | 6 | 2 | 1.000 | 1.000 | 0.333 | 121.833 |

The sample is deliberately small so a reviewer or evaluator can understand the
behavior quickly. Broader model runs can use the same result schema and report
commands.

## Core Commands

```bash
mbs demo
mbs compile examples/fintech_transaction_risk/schema.json
mbs compile examples/fintech_transaction_risk/schema.json --format strict
mbs validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json
mbs check --schema examples/fintech_transaction_risk/schema.json --input "Customer transfers 4800 EUR to a new beneficiary" --model mock
mbs bench --config benchmarks/models.yaml
mbs report --results benchmarks/results/*.json --exclude-infra --require-traces --summary-only
mbs agent-tools --list
mbs make-response-template --cases examples/tool_argument_generation/cases.jsonl --out provider_responses.template.jsonl --output-field tool_call
mbs adapt-responses --schema examples/tool_argument_generation/schema.json --responses provider_responses.jsonl --out provider_responses.mbs.json
python scripts/make_tuning_dataset.py --mbs-result results/hard_agent_routing/provider.mbs.json --cases examples/hard_agent_routing/cases.jsonl --schema examples/hard_agent_routing/schema.json --out results/training/hard_agent_routing_candidates.jsonl
```
- Adapter smoke fixtures: `examples/tool_argument_generation/provider_*_responses.jsonl`

## Docs

- `docs/mbs_evidence_brief.md`
- `docs/mbs_quickstart.md`
- `docs/mbs_bench.md`
- `docs/mbs_public_benchmark_report.md`
- `docs/mbs_lang.md`
- `docs/mbs_model_behavior_guidance.md`
- `docs/mbs_agent_tools.md`
- `docs/mbs_azure_provider_benchmark_may2026.md`
- `docs/mbs_failure_triage_examples.md`
- `docs/mbs_json_mode_tool_calling_plan.md`
- `docs/mbs_open_source_model_testing.md`
- `docs/mbs_training_and_finetuning_path.md`
- `docs/release_notes_v0.1.1.md`

## Why Not Just Validate JSON?

A JSON validator can say whether output parses and matches field types. MBS also
tracks whether the model chose the right enum, omitted required fields, wrapped
JSON in prose, emitted reasoning instead of JSON, produced valid JSON with the
wrong business decision, or became more expensive after retry. That is the
difference between syntax checking and structured-agent-output testing.

## Use In CI

Run MBS before deploying an agent that calls tools or updates records:

```bash
mbs bench --config benchmarks/models.yaml --out benchmarks/results/ci_bench.json
mbs report --results benchmarks/results/ci_bench.json --exclude-infra --require-traces --summary-only
```

Treat easy local mock runs as install/software checks. Treat real-model,
multi-schema, multi-case runs as benchmark evidence only when result JSON files,
trace coverage, failure examples, and cost-per-valid-output reports exist.

## Positioning

Use PASS / FAIL / REVIEW, exact failure reasons, traces, cost per valid output,
and benchmark evidence. Treat numeric reliability scores as experimental until
they are calibrated.
