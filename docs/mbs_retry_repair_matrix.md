# MBS Retry / Repair Matrix

This document describes the deterministic retry/repair matrix for the hard nested tool-argument suite.

## Evidence boundary

`scripts/run_nested_retry_matrix.py` is classified as `fixture_retry_matrix_not_provider_benchmark`.

It proves the MBS retry accounting surface, report generation, retry audit, and regression detection on known fixture rows. It is **not** provider, OSS, or HPC model-behavior evidence.

Real provider/OSS/HPC retry evidence must be generated from real response rows and classified separately.

## Strategies

The fixture matrix writes one MBS result file per strategy:

| Strategy | Meaning |
| --- | --- |
| `no_retry` | Use the first bad fixture output only. |
| `mbs_retry` | Apply the standard MBS fail-closed retry rule to any row that does not pass. |
| `format_retry` | Repair rows that fail JSON/schema validation. |
| `semantic_retry` | Repair schema-clean rows that have the wrong business/tool decision. |
| `best_of_retry` | Select the repaired output whenever the first attempt does not pass. |

## Generated artifacts

Run:

```bash
python scripts/run_nested_retry_matrix.py --out-dir results/nested_retry_matrix_fixture
```

Artifacts:

- `no_retry.mbs.json`
- `mbs_retry.mbs.json`
- `format_retry.mbs.json`
- `semantic_retry.mbs.json`
- `best_of_retry.mbs.json`
- `retry_matrix_summary.json`
- `retry_audit.json`
- `retry_audit.md`
- `triage.json`
- `report.md`
- `manifest.json`

## What the fixture proves

Current 25-case fixture expectations:

- `no_retry`: schema-valid `0.68`, semantic-correct `0.16`.
- `mbs_retry`: schema-valid `1.0`, semantic-correct `1.0` on this deterministic fixture, with retry costs reported separately.
- `format_retry`: schema-valid `1.0`, but semantic failures remain.
- `semantic_retry`: semantic correctness improves over no-retry.
- `best_of_retry`: schema-valid `1.0`, semantic-correct `1.0`.
- Policy metrics include improved rows, unchanged rows, selected-attempt regressions, clean-JSON rate, human-review rate, fail rate, repair-applied rate, and cost per valid output.
- Retry audit must show zero selected-attempt regressions.

The important product point is not that fixtures can be repaired. The point is that MBS reports exactly what changed, what stayed broken, whether selected attempts regressed, and what the next real-evidence gate must be.

## Next real-evidence gate

Run equivalent no-retry/MBS-retry/format-retry/semantic-retry/best-of policies against real provider, OSS, or HPC rows produced by the same hard nested suite. Those artifacts must use `provider`, `oss`, or `hpc` classifications and must include trace coverage, report, retry audit, triage, and gate decisions.
