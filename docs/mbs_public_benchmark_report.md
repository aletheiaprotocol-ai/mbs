# MBS Public Benchmark Report

This report summarizes reproducible structured-output tests for MBS. It is
written for users who want to know what MBS can measure, what it cannot prove
yet, and where real models still fail.

MBS is not a model leaderboard and not a JSON validator. It is testing
infrastructure for structured agent outputs: schema compliance, semantic
correctness, clean JSON behavior, retry cost, failure traces, and cost per valid
output.

## Benchmark Discipline

MBS separates four different things:

- **software tests**: package install, CLI commands, validators, report logic;
- **smoke tests**: tiny infrastructure checks proving a model runner can load a model and write JSON;
- **benchmark tests**: multi-model/multi-case structured-output measurements;
- **failure classes**: infrastructure failure, software bug, benchmark design issue, or real model behavior.

Do not treat a smoke test as benchmark evidence. A benchmark result is usable
only when result JSON files exist, reports generate, traces are present, and
infrastructure failures are separated from behavior rows.

## Local Install / Starter Test

Fresh editable install was tested with:

```bash
python -m pip install -e .
mbs demo
mbs compile examples/fintech_transaction_risk/schema.json --format strict
mbs validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json
mbs check --schema examples/fintech_transaction_risk/schema.json --input "Customer transfers 4800 EUR to a new beneficiary" --model mock
mbs bench --config benchmarks/models.yaml --out benchmarks/results/clean_install_bench.json
mbs report --results benchmarks/results/clean_install_bench.json --require-traces --summary-only --out benchmarks/results/clean_install_report.md
```

This is a **software/install test**, not hard benchmark evidence. It proves a
new user can install MBS and run the basic workflow.

Result after the trace-report fix:

- result files: 1
- report rows: 8
- case runs: 16
- traceable case rows: 16
- missing trace rows: 0
- infra failures: 0

## External GPU Mini Matrix

The first hard benchmark used 5 cached instruction models across 4 schemas.
It intentionally included cases that can fail: invalid enums, invented enums,
missing required fields, wrong types, invalid JSON, prose/reasoning instead of
JSON, and semantic mismatches.

### Models

| family | size / class | exact model id |
| --- | --- | --- |
| Qwen | 3B | `Qwen/Qwen2.5-3B-Instruct` |
| Qwen | 7B | `Qwen/Qwen2.5-7B-Instruct` |
| Gemma | 9B | `google/gemma-2-9b-it` |
| Mistral | 7B | `mistralai/Mistral-7B-Instruct-v0.3` |
| TinyLlama | 1.1B | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` |

### Schemas

- `fintech_transaction_risk`
- `tool_argument_generation`
- `support_ticket_triage`
- `multilingual_risk_review`

### Run metadata

- prompt style: `natural`
- decoding mode: Transformers chat template when available
- language: default schema/case language
- temperature: `0.0`
- seed: `333`
- retry policy: none
- result rows: 20
- case rows: 65
- infrastructure-failed rows: 0
- missing trace rows: 0

### Aggregate result

| metric | value |
| --- | ---: |
| schema-valid rate | 0.5714 |
| semantic-correct rate | 0.7429 |
| clean JSON rate | 0.8143 |
| PASS rows | 40 |
| FAIL rows | 25 |

### Failure classification

| class | count |
| --- | ---: |
| model schema behavior | 13 |
| model format behavior | 7 |
| model semantic behavior | 5 |
| infrastructure failures | 0 |
| known software failures after fixes | 0 |

Top failure types: `invalid_json`, `invalid_enum`, `semantic_mismatch`,
`invented_enum`, `missing_required_key`, and `wrong_type`.

This benchmark did **not** prove that MBS makes every model reliable. It proved
that MBS can expose and classify structured-output failures that look superficially
valid or would be missed by a simple JSON parse.

## Prompt-Style Repair Ablation

The weakest natural-prompt schema was `tool_argument_generation`. A follow-up
ablation tested stronger MBS contracts on the same 5 models.

### Run metadata

- schema: `examples/tool_argument_generation/schema.json`
- prompt styles: `full`, `strict`
- models: same 5-model suite above
- temperature: `0.0`
- seed: `333`
- retry policy: none
- result rows: 10
- case rows: 20
- infrastructure-failed rows: 0
- missing trace rows: 0

### Result

| prompt style | schema-valid rate | semantic-correct rate | clean JSON rate | top failures |
| --- | ---: | ---: | ---: | --- |
| `full` | 0.8 | 0.6 | 1.0 | `semantic_mismatch`, `wrong_type` |
| `strict` | 0.8 | 0.5 | 0.8 | `semantic_mismatch`, `reasoning_prose` |

Model scorecard:

| model | status | schema-valid | semantic-correct | clean JSON | cost / valid output |
| --- | --- | ---: | ---: | ---: | ---: |
| `Qwen/Qwen2.5-3B-Instruct` | PASS | 1.0 | 1.0 | 1.0 | 127.2 |
| `mistralai/Mistral-7B-Instruct-v0.3` | REVIEW | 1.0 | 0.75 | 1.0 | 138.5 |
| `Qwen/Qwen2.5-7B-Instruct` | FAIL | 1.0 | 0.5 | 1.0 | 125.5 |
| `google/gemma-2-9b-it` | FAIL | 1.0 | 0.5 | 1.0 | 126.8 |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | FAIL | 0.0 | 0.0 | 0.5 | n/a |

Interpretation: stronger MBS contracts greatly improved schema validity for the
weakest schema compared with the natural baseline, but they did not eliminate
semantic errors. For TinyLlama, strict prompting caused reasoning/prose failures;
that is model behavior evidence, not a passing result.

## Representative Failure Examples

MBS distinguishes failures that a simple JSON validator would blur together:

- **wrong enum value**: output uses a value outside the schema enum;
- **invented enum value**: model creates a plausible but unsupported action;
- **missing required key**: output omits a required field;
- **wrong type**: field is present but has the wrong JSON type;
- **reasoning prose**: model explains instead of returning raw JSON;
- **semantic mismatch**: JSON is valid but chooses the wrong business/tool decision.

The last category is why a simple JSON validator is not enough. Valid JSON can
still be unsafe or wrong.

## Reproduction Commands

Local starter reproduction:

```bash
python -m pip install -e .
mbs bench --config benchmarks/models.yaml --out benchmarks/results/clean_install_bench.json
mbs report --results benchmarks/results/clean_install_bench.json --require-traces --summary-only --out benchmarks/results/clean_install_report.md
```

Real-model reproduction requires a user-provided model runner or local model
adapter. The public result schema is ordinary JSON and can be aggregated with:

```bash
mbs report --results benchmarks/results/*.json --exclude-infra --require-traces --summary-only
mbs triage --results benchmarks/results/*.json --max-failure-examples 40 --out benchmarks/results/triage_failure_examples.json
```

## What This Proves

MBS can install cleanly, run end-to-end, validate structured output, record
traceable case evidence, aggregate reports, separate infrastructure failures
from model behavior, and expose schema/format/semantic failures across multiple
model families and weights.

## What This Does Not Prove Yet

This does not prove universal reliability, hosted service readiness, native API
JSON-mode parity, tool-calling parity across providers, or broad statistical
claims. Those require larger model suites, sampled decoding, retry/no-retry
ablation, JSON-mode/tool-calling adapters, and repeated seeds.

## Next Benchmark Gate

The next credibility gate is a retry ablation on the same hard cases:

- no retry vs MBS retry;
- deterministic and sampled decoding;
- same model/schema/case IDs;
- report retry improvements and retry regressions;
- keep cost per valid output visible.
