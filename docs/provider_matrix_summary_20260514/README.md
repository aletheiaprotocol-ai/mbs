# MBS Provider Matrix Summary Package — 2026-05-14

This package is a public-safe summary of the May 2026 Azure hard nested provider matrix. It turns the existing provider gate failures into inspectable product evidence without publishing raw provider responses.

## Evidence Boundary

- Classification: `provider` / `real_provider_behavior_evidence_sanitized_summary`.
- Suite: hard nested tool arguments.
- Schema: `examples/nested_tool_arguments/schema.json`.
- Cases: `examples/nested_tool_arguments/cases.jsonl`.
- Case count: 8.
- Runner: `scripts/run_nested_provider_evidence.py`.
- Gate config: `benchmarks/provider_gate.example.yaml`.
- Raw provider artifacts: **not public** in this package.

This is narrow evidence. It proves only how the listed Azure OpenAI deployments behaved on the listed schema, cases, prompt/tool-call contract, gate, and run settings. It does not claim broad model reliability.

## Matrix

| Provider | Deployment | Gate | Schema valid | Semantic correct | Clean JSON | Traceable cases | Infra failures | Primary failure mode | Finding |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Azure OpenAI | `gpt-5-3-chat` | `FAIL` | `1.000` | `0.625` | `1.000` | `8` | `0` | `schema_clean_semantic_mismatch` | Schema-clean tool calls, but semantic tool/priority decisions failed on 3/8 cases. |
| Azure OpenAI | `gpt-5-nano` | `FAIL` | `0.000` | `0.000` | `0.000` | `8` | `0` | `format_schema_failure` | Format/schema failure mode under this hard nested tool-call contract. |
| Azure OpenAI | `gpt-4-1-nano` | `FAIL` | `1.000` | `0.375` | `1.000` | `8` | `0` | `schema_clean_semantic_mismatch` | Schema-clean tool calls, but semantic decisions failed on 5/8 cases. |

## Why Failed Gates Are Useful Here

These rows are not failures of the MBS product. They are the product proof:

- MBS keeps infrastructure failures separate from model behavior.
- MBS shows when tool/function calling is clean JSON but semantically wrong.
- MBS distinguishes schema/format failures from schema-clean semantic failures.
- MBS preserves gate failure status instead of converting it into a pass.

## Files

- `provider_matrix_summary.json` — machine-readable sanitized summary.
- `README.md` — human-readable summary and evidence boundary.

## Non-Claims

- This package does not claim broad provider reliability.
- This package does not claim any listed deployment passed the provider gate.
- This package does not publish raw provider responses.
- This package does not mix fixture evidence with provider behavior evidence.

## Next Step

Run the same hard nested suite against a real local OSS or HPC-served OpenAI-compatible endpoint, classify it as `oss` or `hpc`, and compare failure modes against this Azure matrix.
