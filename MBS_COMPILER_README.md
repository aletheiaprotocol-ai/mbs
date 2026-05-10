# MBS

MBS makes structured agent behavior measurable.

It compiles schemas into minimal behavioral contracts, validates structured
outputs, creates portable traces, reports cost per valid output, and provides a
starter benchmark/test surface for structured-output reliability.

## 30-Second Demo

```bash
pip install -e .
mbs demo
```

Terminal output:

```text
MBS YC demo: structured agent output check

Input prompt:
  Customer says: I think my account was taken over and I cannot sign in.

Check:
  status=FAIL
  failure_type=invalid_enum
  trace_id=mbs_trace_...
  reason=invalid_enum at action
  hint=joined_enum_values

MBS retry repair:
  {"action": "ESCALATE", "priority": "HIGH", "category": "SECURITY", ...}
  status=PASS

Cost/token comparison:
  MBS contract tokens: 62
  Verbose prompt tokens: 164
  Token savings: 62.2%
```

To regenerate the YC artifacts:

```bash
mbs demo --write-artifacts
```

This writes:

- `benchmarks/results/yc_sample_benchmark.json`
- `benchmarks/results/yc_sample_benchmark.md`
- `docs/mbs_yc_evidence_brief.md`

## What MBS Does

MBS is for teams building agents that must produce structured outputs before
they call tools, update records, or trigger workflows.

For each structured output, MBS provides:

- a compact behavioral contract from a schema
- PASS / FAIL / REVIEW validation
- exact failure reasons such as `invalid_enum`, `missing_required_key`, and `wrong_type`
- a trace id with schema, contract, input, and output hashes
- retry and cost-per-valid-output accounting
- strict JSON-only diagnostics for models that wrap JSON in prose or emit reasoning text instead of JSON

## YC Benchmark Sample

Deterministic local sample: 3 support-agent cases x 2 mock model adapters.

| strategy | cases | models | schema-valid | semantic-correct | avg retries | cost / valid output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| verbose prompt | 6 | 2 | 0.500 | 0.500 | 0.000 | 385.0 |
| MBS contract + retry | 6 | 2 | 1.000 | 1.000 | 0.333 | 121.833 |

The sample is deliberately small so a reviewer can understand it quickly. The
larger MN5/Leonardo benchmark reports are tracked separately.

Current MN5 GPU headline snapshot: 18 open instruction/chat/code/MoE models
across 4 schemas and 7 MBS-Lang settings.

| benchmark | no-retry schema-valid | retry schema-valid | no-retry semantic | retry semantic | audit |
| --- | ---: | ---: | ---: | ---: | --- |
| schema/prompt | 0.7321 | 0.9388 | 0.8370 | 0.9203 | compare PASS; retry audit finds 1 Mixtral tool-call regression |
| MBS-Lang | 0.9061 | 0.9603 | 0.8783 | 0.9550 | PASS, 0 selected-attempt regressions |

Reports:

- `benchmarks/results/mn5_eighteen_model_instruction/report_matrix_retry_summary.md`
- `benchmarks/results/mn5_eighteen_model_instruction/report_lang_retry_summary.md`

The same reports now include `clean_json_rate` and `format_risk`, which separate
raw JSON compliance from JSON recovered by extraction. In the 18-model retry
headline, clean JSON is `0.8810` for schema/prompt and `0.9021` for MBS-Lang.
Nemotron 70B is a useful example: it reaches `1.0` schema validity after retry,
but its clean-JSON rate is `0` because every output is recoverable JSON wrapped
in prose, so MBS labels that as REVIEW instead of a clean PASS.

Broader MN5 stress snapshot: 21 models after adding Phi-4 Mini, DeepSeek R1
Distill Qwen 14B, and DeepSeek R1 Distill Qwen 32B. This wider set keeps
weak-model failures visible instead of turning them into a single blended score.

| benchmark | no-retry schema-valid | retry schema-valid | no-retry semantic | retry semantic | audit |
| --- | ---: | ---: | ---: | ---: | --- |
| schema/prompt | 0.6442 | 0.8535 | 0.7444 | 0.8419 | PASS, 0 selected-attempt regressions |
| MBS-Lang | 0.8095 | 0.8519 | 0.7817 | 0.8466 | PASS, 0 selected-attempt regressions |

Latest large-model additions:

| model | MBS result | product signal |
| --- | --- | --- |
| Mixtral 8x22B Instruct | PASS | retry reaches `1.0` schema-valid and clean JSON; MBS-Lang is `1.0` / `1.0` |
| OLMo 2 13B Instruct | PASS | schema/prompt retry is clean JSON `1.0`; MBS-Lang is `1.0` / `1.0` |
| Hermes 3 Llama 3.1 70B | PASS | schema/prompt retry reaches `1.0` schema-valid and clean JSON; MBS-Lang is `1.0` / `1.0` |
| Qwen3-30B-A3B Instruct | PASS | MoE Qwen row: schema/prompt retry reaches `1.0` schema-valid and clean JSON; MBS-Lang is `1.0` / `1.0` |
| Mistral Small 3.1 24B | REVIEW | schema/prompt retry reaches `1.0` schema-valid, but clean JSON remains low because outputs are prose-wrapped |
| Falcon3 10B Instruct | REVIEW | retry improves schema validity, but clean JSON is `0.0` because outputs are fenced/prose-wrapped |
| MiniCPM4 8B | REVIEW | MBS-Lang retry reaches `1.0` schema-valid, but clean JSON remains near zero |
| Phi-4 Reasoning Plus | FAIL | retry cannot recover clean structured output; reasoning prose keeps schema and semantic rates at `0.0` |
| Qwen3 32B | FAIL | strict/retry improves extraction, but clean JSON remains `0.0` because reasoning/prose dominates |
| QwQ 32B | FAIL | retry improves some extracted schema validity, but clean JSON remains `0.0` |
| DeepSeek R1 Distill Llama 70B | FAIL | schema retry reaches only `0.4583` schema-valid / `0.5833` semantic; clean JSON remains `0.0` |

## Core Commands

```bash
mbs demo
mbs compile examples/fintech_transaction_risk/schema.json
mbs compile examples/fintech_transaction_risk/schema.json --format strict
mbs validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json
mbs check --schema examples/fintech_transaction_risk/schema.json --input "Customer transfers 4800 EUR to a new beneficiary" --model mock
mbs bench --config benchmarks/models.yaml
mbs report --results benchmarks/results/*.json --exclude-infra --require-traces --summary-only
```

- `MBS Compiler`: schema to minimal behavioral contract
- `MBS Validate`: exact JSON/schema/enum/type failures
- `MBS Check`: compile, run or mock, validate, trace, cost summary
- `MBS Trace`: audit object for every structured output
- `MBS Cost`: cost per valid structured output
- `MBS Bench`: repeatable structured-output benchmark starter
- `MBS Test`: CI-style structured-output regression command
- `MBS-Lang`: hybrid contracts for multilingual structured-output workflows
- `MBS Report`: aggregate benchmark JSON into Markdown tables, model scorecards, and failure summaries
- `MBS Compare`: detect metric regressions against prior results
- `MBS Models`: enforce broad model-suite coverage
- `MBS Triage`: inspect remote result directories before scaling GPU runs, with issue summaries, capped terminal output, and case-level failure examples

Prompt styles include `natural`, `progressive`, `full`, and `strict`. Use
`strict` when evaluating models that tend to emit analysis, markdown, or prose
around JSON; MBS records `prose_wrapped_json` warnings and `reasoning_prose`
failures so those behaviors remain visible in reports.

MBS is not a full agent runtime, an agent marketplace, or an AI operating system.

## Docs

- `docs/mbs_yc_evidence_brief.md`
- `docs/mbs_quickstart.md`
- `docs/mbs_bench.md`
- `docs/mbs_lang.md`
- `docs/mbs_model_behavior_guidance.md`
- `docs/ci.md`
- `docs/mbs_hpc_compute_plan.md`
- `docs/mbs_remote_stage1_runbook.md`
- `docs/mbs_product_quality_plan.md`

## Positioning

Use PASS / FAIL / REVIEW, exact failure reasons, traces, cost per valid output,
and benchmark evidence. Treat numeric reliability scores as experimental until
they are calibrated.
