# MBS

MBS is a validation compiler that turns LLM outputs into auditable contracts, so
agents fail loudly instead of silently.

MBS is structured-output validation infrastructure for production agents. It
compiles schemas into behavioral contracts, validates structured outputs,
creates portable traces, reports cost per valid output, and provides a
benchmark/test surface for structured-output reliability.

Why now: agent systems increasingly call tools, update records, and trigger
workflows from structured LLM outputs. At scale, valid JSON is not enough; teams
need traces, failure reasons, regression tests, and cost-per-valid-output
evidence.

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

Deterministic local sample: 3 support-agent cases x 2 mock model adapters. This
is a software/demo check, not broad model benchmark evidence.

| strategy | cases | models | schema-valid | semantic-correct | avg retries | cost / valid output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| verbose prompt | 6 | 2 | 0.500 | 0.500 | 0.000 | 385.0 |
| MBS contract + retry | 6 | 2 | 1.000 | 1.000 | 0.333 | 121.833 |

The sample is deliberately small so a reviewer or evaluator can understand the
behavior quickly. Broader model runs can use the same result schema and report
commands.

Methodology: the sample uses fixed local fixtures in `benchmarks/models.yaml` and
`examples/support_ticket_triage/`. Real provider evidence is documented in
`docs/mbs_azure_provider_benchmark_may2026.md` and should be interpreted only for
the tested schema, cases, modes, deployments, and run settings.

## Core Commands

```bash
mbs demo
mbs compile examples/fintech_transaction_risk/schema.json
mbs compile examples/fintech_transaction_risk/schema.json --format strict
mbs validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json
mbs check --schema examples/fintech_transaction_risk/schema.json --input "Customer transfers 4800 EUR to a new beneficiary" --model mock
mbs bench --config benchmarks/models.yaml
mbs report --results benchmarks/results/*.json --exclude-infra --require-traces --summary-only
mbs evidence-pack --results benchmarks/results/ci_bench.json --gate-config benchmarks/ci_gate.yaml --classification ci --out-dir benchmarks/results/evidence_pack_ci
mbs agent-tools --list
mbs make-response-template --cases examples/tool_argument_generation/cases.jsonl --out provider_responses.template.jsonl --output-field tool_call
mbs adapt-responses --schema examples/tool_argument_generation/schema.json --cases examples/tool_argument_generation/cases.jsonl --responses provider_responses.jsonl --model provider-model --decoding-mode tool_call --out provider_responses.mbs.json
python scripts/run_nested_tool_fixture_pack.py --out-dir results/nested_tool_fixture_pack
python scripts/run_nested_provider_evidence.py --responses results/provider_nested_tool_call.responses.jsonl --model provider-or-oss-model-id --classification provider --mode tool_call --out-dir results/nested_provider_evidence
python scripts/build_nested_provider_evidence.py --responses results/provider_nested_tool_call.responses.jsonl --model provider-or-oss-model-id --decoding-mode tool_call --classification provider --gate-config benchmarks/provider_gate.example.yaml --out-dir results/nested_provider_evidence
python scripts/assert_ci_artifacts.py --results-dir benchmarks/results
python scripts/make_tuning_dataset.py --mbs-result results/hard_agent_routing/provider.mbs.json --cases examples/hard_agent_routing/cases.jsonl --schema examples/hard_agent_routing/schema.json --out results/training/hard_agent_routing_candidates.jsonl
python scripts/analyze_mbs_failures.py --results "results/hard_agent_routing/**/*.mbs.json" --cases examples/hard_agent_routing/cases.jsonl --out-md results/hard_agent_routing/failure_analysis.md --out-csv results/hard_agent_routing/failure_analysis.csv
```
- Adapter smoke fixtures: `examples/tool_argument_generation/provider_*_responses.jsonl`
- Hard nested tool-call fixtures: `examples/nested_tool_arguments/` eight-case suite with nested arrays, strict extra-key blocking, enum traps, and semantic mismatch fixtures
- Hard nested provider/OSS evidence builder: `scripts/build_nested_provider_evidence.py`
- One-command hard nested provider/OSS runner: `scripts/run_nested_provider_evidence.py`
- CI artifact completeness gate: `scripts/assert_ci_artifacts.py`

## Docs

- `docs/mbs_evidence_brief.md`
- `docs/mbs_quickstart.md`
- `docs/mbs_bench.md`
- `docs/mbs_public_benchmark_report.md`
- `docs/mbs_evidence_pack.md`
- `docs/mbs_lang.md`
- `docs/mbs_model_behavior_guidance.md`
- `docs/mbs_agent_tools.md`
- `docs/mbs_provider_recipes.md`
- `docs/mbs_ci_regression_gate.md`
- `docs/mbs_nested_provider_matrix_may2026.md`
- `docs/mbs_azure_provider_benchmark_may2026.md`
- `docs/mbs_failure_triage_examples.md`
- `docs/mbs_json_mode_tool_calling_plan.md`
- `docs/mbs_open_source_model_testing.md`
- `docs/mbs_mn5_vs_azure_comparison_may2026.md`
- `docs/mbs_oss_mn5_benchmark_may2026.md`
- `docs/mbs_hard_agent_routing_label_review_may2026.md`
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
python -m pip install -e ".[test]"
python -m pytest -q
mbs bench --config benchmarks/models.yaml --out benchmarks/results/ci_bench.json
mbs report --results benchmarks/results/ci_bench.json --exclude-infra --require-traces --summary-only
mbs gate --results benchmarks/results/ci_bench.json --config benchmarks/ci_gate.yaml
```

The repository includes a ready-to-copy GitHub Actions workflow at
`.github/workflows/mbs-ci.yml`. See `docs/mbs_ci_regression_gate.md` for the
CI evidence boundary and `docs/mbs_provider_recipes.md` for text, JSON-mode,
and tool-call provider response flows. For real provider or OSS gates, start
from `benchmarks/provider_gate.example.yaml` and tune thresholds explicitly for
the application risk.

Treat easy local mock runs as install/software checks. Treat real-model,
multi-schema, multi-case runs as benchmark evidence only when result JSON files,
trace coverage, failure examples, and cost-per-valid-output reports exist.

## Positioning

Use PASS / FAIL / REVIEW, exact failure reasons, traces, cost per valid output,
and benchmark evidence. Treat numeric reliability scores as experimental until
they are calibrated.
