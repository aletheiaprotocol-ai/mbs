# MBS Bench

MBS Bench measures structured-output reliability across schemas, cases, models, prompt styles, decoding modes, and languages.

## Local Config

```yaml
schema: examples/fintech_transaction_risk/schema.json
cases: examples/fintech_transaction_risk/cases.jsonl
models:
  - mock
prompt_styles:
  - full
  - natural
  - progressive
decoding_modes:
  - local_mock
languages:
  - en
  - ar
```

Run it:

```bash
mbs bench --config benchmarks/models.yaml --out benchmarks/results/local_bench.json
mbs report --results benchmarks/results/*.json --out benchmarks/results/local_report.md
mbs report --results benchmarks/results/*.json --exclude-infra --require-traces --out benchmarks/results/local_behavior_report.md
mbs report --results benchmarks/results/*.json --exclude-infra --require-traces --summary-only --out benchmarks/results/local_scorecard.md
```

## Case Format

```json
{
  "id": "tx_001",
  "input": "Customer transfers 4800 EUR to a new beneficiary",
  "expected_valid_outputs": ["REVIEW", "ESCALATE", "BLOCK"],
  "semantic_label": "high_risk_new_beneficiary"
}
```

## Metrics

MBS Bench reports valid JSON rate, schema-valid rate, enum accuracy, required-key accuracy, semantic correctness, latency, contract tokens, verbose baseline tokens, cost per valid output, and failure types.
When retry mode is used, reports also include average retry count so cost-per-valid-output can be interpreted against the number of corrective generations. Retry cost accounting charges the input contract once per attempt plus generated output tokens.

If a config omits `prompt_styles`, `mbs bench` defaults to `full`. Keep
`natural` and `progressive` in explicit configs for controlled comparisons,
not as the product default.

For product claims, prefer reports generated with:

```bash
mbs report --results "benchmarks/results/**/*.json" --exclude-infra --require-traces
```

`--exclude-infra` keeps missing model caches and load failures out of behavior averages. `--require-traces` returns nonzero if case rows are not tied to trace ids and token records.

`--summary-only` emits the model PASS/REVIEW/FAIL scorecard and aggregate failure summary without the full row table. Use this for launch notes and daily compute reviews.

Use `mbs triage --max-failure-examples N --out triage.json` to export concrete
failed case ids, trace ids, failure types, and first validation details.

Use `benchmarks/local_fintech_baselines.yaml` to compare the starter prompt styles:

```bash
mbs bench --config benchmarks/local_fintech_baselines.yaml --out benchmarks/results/fintech_baselines.json
mbs report --results benchmarks/results/fintech_baselines.json
```

## Broad Model Suites

MBS benchmark evidence should not depend on a tiny model sample. Model suites live in:

```text
benchmarks/model_suites.json
```

Export the broad Stage 1 suite:

```bash
mbs models \
  --suite stage1_broad \
  --min-models 30 \
  --min-families 10 \
  --min-size-bands 3 \
  --out benchmarks/stage1_models.txt
```

The broad suite currently covers 37 models across 17 families. The large suite
covers 14 larger/MoE models across 11 families. Use the exported model list with
your own model adapter or evaluation harness.

For retry/cost experiments, keep the no-retry baseline and compare it with a
separate retry run using the same cases, schema, and model adapter.

## Failure Types

```text
invalid_json
missing_required_key
invalid_enum
invented_enum
wrong_type
extra_key
semantic_mismatch
language_mismatch
refusal
timeout
overlong_output
prompt_injection_followed
```

## Compute Gate

Use local/dev runs for harness validation. Scale model runs only after configs,
cases, semantic labels, and result schemas are stable.
