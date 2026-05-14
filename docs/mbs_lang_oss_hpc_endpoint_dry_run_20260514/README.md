# MBS-Lang OSS/HPC Endpoint Dry Run — 2026-05-14

This package records readiness for running MBS-Lang against a real OSS/HPC OpenAI-compatible endpoint.

No reachable endpoint was available during this check, so this package intentionally records **no model-behavior evidence**.

## Endpoint Probe

Checked common local OpenAI-compatible URLs:

| URL | Result |
| --- | --- |
| `http://127.0.0.1:8000/v1/models` | not reachable |
| `http://127.0.0.1:1234/v1/models` | not reachable |
| `http://127.0.0.1:11434/v1/models` | not reachable |
| `http://localhost:8000/v1/models` | not reachable |

## Dry-Run Plan

The planned real run shape is:

```bash
python scripts/run_lang_provider_evidence.py \
  --provider openai-compatible \
  --endpoint http://127.0.0.1:8000 \
  --model local-oss-openai-compatible-placeholder \
  --classification oss \
  --mode json_mode \
  --out-dir results/mbs_lang_oss_endpoint_dry_run_20260514
```

The actual command was run with `--dry-run --json`, so it wrote a plan only and did not call a model.

## Evidence Boundary

- Raw responses collected: **no**.
- Evidence pack created: **no**.
- Aggregate matrix row created: **no**.
- OSS/HPC MBS-Lang benchmark claim: **no**.

This record exists to prevent accidental fabrication. It proves the MBS-Lang harness path is prepared for OSS/HPC endpoints, but it does not claim any OSS/HPC model passed or failed MBS-Lang.

## Required For Real Evidence

1. Start a real OpenAI-compatible endpoint exposing `/v1/models` and chat completions.
2. Use a real served model id.
3. Run `scripts/run_lang_provider_evidence.py` without `--dry-run`.
4. Use `--classification oss` for local/open OSS models or `--classification hpc` for HPC-served models.
5. Keep raw `results/` private until sanitized release review.
6. Publish only aggregate sanitized rows unless raw responses are explicitly scrubbed and approved.

## Files

- `endpoint_dry_run.json` — machine-readable no-evidence dry-run record.
- `README.md` — human-readable evidence boundary and next steps.
