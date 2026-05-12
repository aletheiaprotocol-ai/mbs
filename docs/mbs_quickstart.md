# MBS Quickstart

MBS turns a JSON Schema into a compact behavioral contract, validates model output, records a trace, and reports cost per valid structured output.

The user-facing default is the `full` contract style because current benchmark
evidence makes it the safest baseline. Use `--format natural` only when you are
explicitly measuring compact/cheap contracts.

## Install

```bash
git clone https://github.com/aletheiaprotocol-ai/mbs.git
cd mbs
python -m pip install -e . --no-deps
```

## Run The Demo

```bash
mbs demo
```

This prints one end-to-end flow: schema + prompt, minimal behavioral contract,
model output, PASS / FAIL / REVIEW result, trace id, retry repair, and token
comparison. To regenerate the sample benchmark and one-page evidence brief:

```bash
mbs demo --write-artifacts
```

## Compile A Contract

```bash
mbs compile examples/fintech_transaction_risk/schema.json
```

## Validate Output

```bash
mbs validate \
  --schema examples/fintech_transaction_risk/schema.json \
  --output examples/fintech_transaction_risk/output.json
```

## Check One Case

```bash
mbs check \
  --schema examples/fintech_transaction_risk/schema.json \
  --input "Customer transfers 4800 EUR to a new beneficiary" \
  --model mock \
  --json
```

## Run The Starter Benchmark

```bash
mbs bench --config benchmarks/models.yaml
mbs report --results benchmarks/results/*.json --out benchmarks/results/local_report.md
mbs report --results benchmarks/results/*.json --exclude-infra --require-traces --summary-only --out benchmarks/results/local_scorecard.md
```

The scorecard report ranks models with PASS / REVIEW / FAIL and lists the dominant failure types without printing every benchmark row. It also includes `clean_json_rate` and `format_risk`, so prose-wrapped JSON and reasoning text do not get hidden behind extraction-assisted schema-valid rates.

This starter benchmark is an install/software check. It is intentionally small
and uses a local mock adapter. Do not treat it as hard model evidence. For hard
evidence, use multiple schemas, multiple cases, real model families/weights,
prompt-style comparisons, retry/no-retry comparisons, trace coverage, and
failure examples.

See `docs/mbs_public_benchmark_report.md` for the current public benchmark
discipline and example report format.

## Run Regression Tests

```bash
mbs test \
  --schemas examples/fintech_transaction_risk \
  --cases examples/fintech_transaction_risk/cases.jsonl \
  --models benchmarks/models.yaml
```

## Show Exact Failure Reasons

```bash
mbs bench \
  --schema examples/regression_enum_failure/schema.json \
  --cases examples/regression_enum_failure/cases.jsonl \
  --out benchmarks/results/regression_enum_failure.json

mbs report --results benchmarks/results/regression_enum_failure.json
```

This demo intentionally produces `invented_enum` and `missing_required_key` failures.

For case-level failure export:

```bash
mbs triage \
  --results benchmarks/results/*.json \
  --max-failure-examples 40 \
  --out benchmarks/results/triage_failure_examples.json
```

Compare against a known-good baseline:

```bash
mbs compare \
  --baseline benchmarks/results/regression_enum_baseline.json \
  --current benchmarks/results/regression_enum_failure.json
```

For prompt-style ablations, the prompt style intentionally changes. In that
case, match on stable identity fields while keeping prompt style visible as the
changed dimension:

```bash
mbs compare \
  --baseline benchmarks/results/natural/*.json \
  --current benchmarks/results/strict/*.json \
  --match-on schema,model,decoding_mode,language
```

If no rows match, `mbs compare` returns `NO_MATCH` and exits nonzero. This
prevents an empty comparison from being mistaken for a passing regression check.

Current scope is local correctness and reproducibility. Real model adapters
should start only after this harness is stable.

## Use From Agent Runtimes

```bash
mbs agent-tools --list
```

For Python wrappers and MCP-style integrations, see `docs/mbs_agent_tools.md`.
