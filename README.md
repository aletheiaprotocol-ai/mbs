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
```

## Docs

- `docs/mbs_evidence_brief.md`
- `docs/mbs_quickstart.md`
- `docs/mbs_bench.md`
- `docs/mbs_lang.md`
- `docs/mbs_model_behavior_guidance.md`
- `docs/mbs_agent_tools.md`

## Positioning

Use PASS / FAIL / REVIEW, exact failure reasons, traces, cost per valid output,
and benchmark evidence. Treat numeric reliability scores as experimental until
they are calibrated.
