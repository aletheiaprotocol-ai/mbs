# MBS Evidence Packs

An MBS evidence pack is a small directory that bundles the artifacts a reviewer
needs to inspect a structured-output test run.

It is meant for pull requests, buyer demos, provider runs, OSS/HPC benchmark
runs, and release review.

## Create A CI Evidence Pack

```bash
mbs bench --config benchmarks/models.yaml --out benchmarks/results/ci_bench.json
mbs evidence-pack \
  --results benchmarks/results/ci_bench.json \
  --gate-config benchmarks/ci_gate.yaml \
  --classification ci \
  --copy-results \
  --out-dir benchmarks/results/evidence_pack_ci
```

The pack writes:

- `README.md` — human-readable summary and evidence boundary;
- `manifest.json` — machine-readable manifest;
- `report.md` and `report.json` — scorecards and aggregate metrics;
- `gate.md` and `gate.json` — threshold pass/fail evidence when a gate config is provided;
- `triage.md` and `triage.json` — failure review and trace review;
- `raw_results/` — copied result JSON files when `--copy-results` is used.

## Evidence Classifications

Use the right classification so claims stay honest:

| classification | Meaning |
| --- | --- |
| `demo` | Demo/software check, not model benchmark evidence. |
| `ci` | CI regression check, not broad model benchmark evidence. |
| `fixture` | Fixture smoke test, not provider benchmark evidence. |
| `provider` | Real provider behavior evidence for listed schemas/cases/settings only. |
| `oss` | Open-source model behavior evidence for listed models/settings only. |
| `hpc` | HPC model behavior evidence for listed models/settings only. |

## Provider Evidence Pack

```bash
mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses provider_responses.jsonl \
  --model your-provider-model \
  --decoding-mode tool_call \
  --out benchmarks/results/provider_tool_call.mbs.json

mbs evidence-pack \
  --results benchmarks/results/provider_tool_call.mbs.json \
  --gate-config benchmarks/provider_gate.example.yaml \
  --classification provider \
  --copy-results \
  --out-dir benchmarks/results/evidence_pack_provider
```

A provider evidence pack may support model-behavior claims only for the exact
schemas, cases, model, decoding mode, and run settings in the result files. It is
not a general provider benchmark unless the run design is broad enough and the
manifest/report make that clear.

For hard nested tool-call evidence, use the one-command runner so the response
JSONL, adapted MBS result, gate, triage, evidence pack, and run manifest stay
together:

```bash
python scripts/run_nested_provider_evidence.py \
  --provider openai-compatible \
  --endpoint http://127.0.0.1:8000 \
  --model your-local-oss-model \
  --classification oss \
  --mode tool_call \
  --out-dir results/nested_provider_evidence_oss
```

Use `--classification provider`, `oss`, or `hpc` only for real model behavior.
Fixture rows are software checks and should remain `fixture`.

## When The Pack Fails

`mbs evidence-pack` exits nonzero if required trace checks fail or if the included
gate fails. Treat that as useful evidence. Inspect:

- `gate.md` for threshold failures;
- `report.md` for scorecards;
- `triage.md` for concrete failure examples and trace problems.

## Sanitized Release Packages

Raw provider responses may contain proprietary prompts, model outputs, endpoint
metadata, or operational details. A sanitized release package should publish the
reviewable claim boundary without copying raw `results/` directories unless they
are intentionally scrubbed and approved.

Minimum public package contents:

- a release manifest with included docs and excluded raw artifacts;
- the exact schema, cases, runner, gate config, model/deployment ids, mode, and
  classification used;
- aggregate matrix rows, gate status, and failure-mode summaries;
- explicit non-claims and next evidence gates;
- validation records for tests, CI, and any public dashboard deployment.

The May 2026 hard nested package is documented in
`docs/mbs_sanitized_evidence_release_may2026.md`.
