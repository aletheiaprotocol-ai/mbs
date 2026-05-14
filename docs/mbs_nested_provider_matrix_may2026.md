# MBS Hard Nested Provider Matrix — May 2026

This note summarizes a small real-provider behavior matrix for the hard nested
tool-call suite in `examples/nested_tool_arguments/`.

It is intentionally narrow evidence. It does **not** claim broad model
reliability. It proves only how the listed Azure OpenAI deployments behaved on
the listed eight cases, schema, tool-call prompt contract, gate configuration,
and run settings.

Raw provider responses and run artifacts are kept under local ignored
`results/` directories. Do not commit API keys, bearer tokens, cloud request
headers, or raw provider logs that might contain sensitive metadata.

## Evidence Boundary

- Classification: `provider` / `real_provider_behavior_evidence`.
- Suite: hard nested tool arguments with nested objects, arrays of actions,
  strict extra-key blocking, enum traps, prompt-injection text, and
  schema-clean semantic mismatch cases.
- Schema: `examples/nested_tool_arguments/schema.json`.
- Cases: `examples/nested_tool_arguments/cases.jsonl`.
- Runner: `scripts/run_nested_provider_evidence.py`.
- Gate: `benchmarks/provider_gate.example.yaml`.
- Thresholds include trace coverage, `min_traceable_case_rows: 8`,
  `min_total_runs: 8`, schema-valid rate, semantic-correct rate, clean-JSON
  rate, and zero hidden infra failures.

## Azure Matrix Summary

Machine-readable sanitized package:
`docs/provider_matrix_summary_20260514/provider_matrix_summary.json`.

| Deployment | Gate | Schema valid | Semantic correct | Clean JSON | Traceable cases | Infra failures | Main finding |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `gpt-5-3-chat` | `FAIL` | `1.0` | `0.625` | `1.0` | `8` | `0` | Schema-clean tool calls, but semantic tool/priority decisions failed on 3/8 cases. |
| `gpt-5-nano` | `FAIL` | `0.0` | `0.0` | `0.0` | `8` | `0` | Format/schema failure mode under this hard tool-call contract. |
| `gpt-4-1-nano` | `FAIL` | `1.0` | `0.375` | `1.0` | `8` | `0` | Schema-clean tool calls, but semantic decisions failed on 5/8 cases. |

All three rows are useful evidence because the failures are not hidden:

- `gpt-5-3-chat` and `gpt-4-1-nano` show why JSON/tool-call validity is not the
  same as correct agent behavior.
- `gpt-5-nano` shows a separate format/schema failure mode.
- All runs have traceable cases and zero recorded infrastructure failures.

## Local Artifact Paths

These paths are local ignored artifacts, not committed source files:

- `results/nested_provider_evidence_azure_gpt_5_3_chat_20260514_v2/`
- `results/nested_provider_evidence_azure_gpt_5_nano_20260514/`
- `results/nested_provider_evidence_azure_gpt_4_1_nano_20260514/`

Each run writes:

- `nested_provider.responses.jsonl` — raw provider response rows;
- `nested_provider.mbs.json` — adapted MBS result;
- `report.md` — aggregate report;
- `gate.json` — threshold result;
- `triage.json` — concrete failures;
- `manifest.json` — evidence boundary and checks;
- `run_manifest.json` — wrapper status and command metadata;
- `evidence_pack/` — reviewable evidence bundle.

## Reproduction Pattern

Dry-run first:

```bash
python scripts/run_nested_provider_evidence.py \
  --provider azure \
  --model azure-deployment-name \
  --deployment azure-deployment-name \
  --classification provider \
  --mode tool_call \
  --out-dir results/nested_provider_evidence_azure_deployment \
  --dry-run \
  --json
```

Run for real:

```bash
python scripts/run_nested_provider_evidence.py \
  --provider azure \
  --model azure-deployment-name \
  --deployment azure-deployment-name \
  --classification provider \
  --mode tool_call \
  --out-dir results/nested_provider_evidence_azure_deployment \
  --json
```

If the provider gate fails, the command exits nonzero but still writes the
reviewable artifacts listed above. This is deliberate: CI can block the run while
humans can inspect exactly why it failed.

## Next Matrix Step

Run the same eight cases against an OpenAI-compatible local OSS endpoint or an
HPC-served OSS model, classify it as `oss` or `hpc`, and compare failure modes
without mixing fixture evidence into provider/model-behavior claims.