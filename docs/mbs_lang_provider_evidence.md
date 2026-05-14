# MBS-Lang Provider Evidence Flow

This document describes the provider/OSS/HPC-ready path for multilingual MBS evidence.

## Evidence Boundary

The local fixture response file proves the MBS-Lang evidence pipeline only:

- response JSONL adaptation;
- per-row `input_language`, `output_language`, and `contract_language` preservation;
- report/gate/triage/manifest generation;
- evidence-pack creation with copied raw result JSON.

It does **not** prove provider/model reliability, OSS/HPC behavior, or translation quality.

Real claims require `--classification provider`, `--classification oss`, or `--classification hpc` with real response rows from the listed model, mode, endpoint, schema, cases, and gate.

## Fixture Path Validation

```bash
python scripts/run_lang_provider_evidence.py \
  --responses examples/multilingual_risk_review/provider_json_mode_good.jsonl \
  --model fixture-lang-provider \
  --classification fixture \
  --mode json_mode \
  --out-dir results/mbs_lang_provider_evidence
```

Current fixture result:

- Classification label: `fixture_mbs_lang_not_provider_benchmark`
- Rows: `15`
- Languages: `ar`, `de`, `en`, `es`, `fr`, `hu`, `tr`
- Domains: `fintech`, `procurement`, `qme_source_review`, `support`, `tool_call_safety`
- Schema-valid rate: `1.0`
- Semantic-correct rate: `1.0`
- Clean-JSON rate: `1.0`
- Gate status: `PASS`
- Triage status: `PASS`
- Trace errors: `0`
- Evidence pack classification: `fixture_smoke_not_provider_benchmark`

## Real Provider / OSS / HPC Path

Collect or reuse responses, then build classified evidence:

```bash
python scripts/run_lang_provider_evidence.py \
  --responses results/mbs_lang_provider.responses.jsonl \
  --model provider-or-oss-model-id \
  --classification provider \
  --mode json_mode \
  --gate-config benchmarks/provider_lang_gate.example.yaml \
  --out-dir results/mbs_lang_provider_evidence
```

To inspect planned collection commands without calling a provider:

```bash
python scripts/run_lang_provider_evidence.py \
  --model provider-or-oss-model-id \
  --provider openai-compatible \
  --endpoint http://127.0.0.1:8000 \
  --classification oss \
  --mode json_mode \
  --out-dir results/mbs_lang_provider_evidence \
  --dry-run
```

## Required Artifacts

A reviewable MBS-Lang behavior claim should include:

- `run_plan.json`
- `run_manifest.json`
- `manifest.json`
- `mbs_lang_provider.mbs.json`
- `report.md`
- `gate.json`
- `triage.json`
- `evidence_pack/manifest.json`
- copied raw result JSON when public release is intentional and sanitized

## Provider Gate

Use `benchmarks/provider_lang_gate.example.yaml` as the starting point. Copy and tune it for the target application risk; do not silently lower thresholds after seeing failures.

The example gate is aligned to the current 15-row multilingual fixture surface and requires at least 15 total runs / traceable case rows for a real provider, OSS, or HPC behavior claim.

## Sanitized Public Summary

The expanded 15-row provider summary is published at `docs/mbs_lang_provider_expanded_summary_20260514/README.md`.

It records a real Azure `gpt-5-3-chat` JSON-mode provider run on the current 15-row suite. The gate failed honestly because one Arabic tool-call-safety row triggered provider content filtering. Raw provider response JSONL is not included in the public package.

The first sanitized provider summary is published at `docs/mbs_lang_provider_summary_20260514/README.md`.

It records historical seven-case Azure provider runs with complete trace coverage for the earlier MBS-Lang surface, while keeping raw provider response JSONL out of the public package. New provider/OSS/HPC runs should use the current 15-row suite and the updated provider language gate.
