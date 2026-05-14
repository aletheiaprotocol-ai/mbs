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
- Rows: `7`
- Languages: `ar`, `de`, `en`, `es`, `fr`, `hu`, `tr`
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
