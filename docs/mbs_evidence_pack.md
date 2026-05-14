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

## When The Pack Fails

`mbs evidence-pack` exits nonzero if required trace checks fail or if the included
gate fails. Treat that as useful evidence. Inspect:

- `gate.md` for threshold failures;
- `report.md` for scorecards;
- `triage.md` for concrete failure examples and trace problems.
