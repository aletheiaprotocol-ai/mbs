# MBS Sanitized Evidence Release Package — May 2026

This package is the public, sanitized release boundary for the May 2026 MBS hard
nested provider evidence work. It is designed for reviewers who need to inspect
what was tested, what failed, what was published, and what remains private.

It does **not** publish raw provider responses. Raw `results/` directories remain
ignored/local unless intentionally scrubbed and approved for release.

## Included Public Artifacts

| Artifact | Purpose |
| --- | --- |
| `examples/nested_tool_arguments/schema.json` | Strict nested tool-argument schema with extra-key blocking. |
| `examples/nested_tool_arguments/cases.jsonl` | Eight hard nested tool-call cases. |
| `scripts/run_nested_provider_evidence.py` | One-command collection/build runner. |
| `scripts/build_nested_provider_evidence.py` | Classified evidence-pack builder for provider/OSS/HPC/fixture rows. |
| `benchmarks/provider_gate.example.yaml` | Real provider/OSS/HPC example gate with trace and behavior coverage. |
| `docs/mbs_nested_provider_matrix_may2026.md` | Sanitized three-deployment Azure matrix summary. |
| `docs/provider_matrix_summary_20260514/` | Public-safe JSON + Markdown provider matrix summary package. |
| `docs/mbs_provider_recipes.md` | Provider, OpenAI-compatible, and local OSS endpoint guidance. |
| `docs/mbs_evidence_pack.md` | Evidence-pack and sanitized-release packaging guidance. |

## Excluded Private Artifacts

The following stay private by default:

- raw provider response JSONL files;
- ignored `results/nested_provider_evidence_*` directories;
- endpoint URLs beyond public-safe examples;
- API keys, account metadata, and environment variables;
- unreviewed model outputs that may contain proprietary prompt or response text.

## Evidence Boundary

The current public matrix is narrow evidence:

- classification: `provider` / `real_provider_behavior_evidence`;
- suite: hard nested tool arguments;
- cases: eight cases in `examples/nested_tool_arguments/cases.jsonl`;
- mode: `tool_call`;
- gate: `benchmarks/provider_gate.example.yaml`;
- providers/deployments: the three Azure deployments listed in
  `docs/mbs_nested_provider_matrix_may2026.md`.

It does **not** claim broad provider reliability, production readiness, or model
superiority. The published Azure matrix documents honest provider gate failures.

## Public Matrix Status

| Deployment | Gate | Schema valid | Semantic correct | Clean JSON | Traceable cases | Infra failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `gpt-5-3-chat` | FAIL | 1.000 | 0.625 | 1.000 | 8 | 0 |
| `gpt-5-nano` | FAIL | 0.000 | 0.000 | 0.000 | 8 | 0 |
| `gpt-4-1-nano` | FAIL | 1.000 | 0.375 | 1.000 | 8 | 0 |

Interpretation: the runs are infrastructure-clean and traceable, but the tested
deployments did not pass the configured behavior gate.

## Gate Hardening In This Package

The provider gate now supports `min_behavior_rows` in addition to existing row,
trace, model, schema, metric, and infrastructure-failure thresholds. This blocks
infra-only artifacts from satisfying row coverage when a real behavior row is
required.

`benchmarks/provider_gate.example.yaml` sets:

- `min_rows: 1`
- `min_behavior_rows: 1`
- `min_traceable_case_rows: 8`
- `min_total_runs: 8`
- `max_missing_trace_rows: 0`
- `max_uncheckable_result_rows: 0`
- `max_infra_failed_rows: 0`

## Reproduction Pattern

Dry-run the public command shape without calling a provider:

```bash
python scripts/run_nested_provider_evidence.py \
  --provider openai-compatible \
  --endpoint http://127.0.0.1:8000 \
  --model your-local-oss-model \
  --classification oss \
  --mode tool_call \
  --dry-run \
  --json
```

For Azure or other real providers, keep credentials in environment variables and
store raw outputs under ignored `results/` paths until release review.

## Validation Record

At package creation:

- full public test suite passed locally;
- public GitHub Actions `MBS CI` was green for the matrix documentation commit;
- the public evidence dashboard deployed version `2026-05-14.5` and exposed the
  matrix link and proof-limit text on both workers.dev and the custom domain.

## Next Evidence Gate

Run the same hard nested suite against a local OSS or HPC-served
OpenAI-compatible endpoint, classify it as `oss` or `hpc`, and compare failure
modes against the Azure matrix without mixing fixture evidence into model
behavior claims.