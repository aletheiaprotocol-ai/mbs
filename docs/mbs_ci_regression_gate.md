# MBS CI Regression Gate

This workflow turns MBS into a structured-output regression gate for agents.
It is designed to be copy/paste safe for GitHub Actions and intentionally uses
local deterministic fixtures by default.

## What The Gate Proves

The default CI gate proves software and integration health:

- package installs;
- unit and conformance tests pass;
- demo artifacts regenerate;
- benchmark JSON is produced;
- report generation succeeds;
- case rows have trace ids;
- CI artifacts are downloadable.

It does **not** prove broad model reliability. Real-model evidence still needs
provider/OSS response files, repeated cases, trace coverage, failure examples,
cost reports, and documented reproduction commands.

## Copy/Paste GitHub Actions Workflow

The repository includes `.github/workflows/mbs-ci.yml`.

Core commands:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
mbs demo --write-artifacts
mbs bench --config benchmarks/models.yaml --out benchmarks/results/ci_bench.json
mbs report --results benchmarks/results/ci_bench.json --exclude-infra --require-traces --summary-only --out benchmarks/results/ci_report.md
mbs gate --results benchmarks/results/ci_bench.json --config benchmarks/ci_gate.yaml --out benchmarks/results/ci_gate.json
```

The `.[test]` extra installs the test runner used by CI. A clean GitHub runner
does not inherit local development packages.

## Recommended Pull Request Rule

Block merge if any of these fail:

1. Python tests fail.
2. `mbs bench` does not produce result JSON.
3. `mbs report --require-traces` exits nonzero.
4. `mbs gate` misses configured thresholds.
5. CI artifacts are missing.

## Threshold Config

The included `benchmarks/ci_gate.yaml` is intentionally strict because the
default CI run is deterministic local mock data:

```yaml
thresholds:
  require_rows: true
  require_traces: true
  min_schema_valid_rate: 1.0
  min_semantic_correct_rate: 1.0
  min_clean_json_rate: 1.0
  max_missing_trace_rows: 0
  max_uncheckable_result_rows: 0
  max_infra_failed_rows: 0
```

For real providers or open-source models, use a separate config that matches the
risk of that application. Do not loosen thresholds silently; document why a lower
threshold is acceptable and keep the raw result JSON.

## Adding A Real Agent Gate

For your own agent, replace `benchmarks/models.yaml` with a config that points to
your schemas and cases, or adapt provider responses first:

```bash
mbs make-response-template \
  --cases examples/tool_argument_generation/cases.jsonl \
  --out provider_responses.template.jsonl \
  --output-field tool_call

mbs adapt-responses \
  --schema examples/tool_argument_generation/schema.json \
  --cases examples/tool_argument_generation/cases.jsonl \
  --responses provider_responses.jsonl \
  --model your-provider-model \
  --decoding-mode tool_call \
  --out benchmarks/results/provider_tool_call.mbs.json

mbs report --results benchmarks/results/provider_tool_call.mbs.json --exclude-infra --require-traces
mbs triage --results benchmarks/results/provider_tool_call.mbs.json --out benchmarks/results/provider_triage.json
```

## Evidence Boundary

Use CI output as software/regression evidence. Use real-provider or OSS result
JSON plus reports as model-behavior evidence only when the run design is clear
and failures are not hidden.
