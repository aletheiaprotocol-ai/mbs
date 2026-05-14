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
- CI artifacts are downloadable;
- hard nested tool-call fixture packs are generated;
- artifact manifests preserve evidence boundaries.

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
mbs evidence-pack --results benchmarks/results/ci_bench.json --gate-config benchmarks/ci_gate.yaml --classification ci --copy-results --out-dir benchmarks/results/evidence_pack_ci
python scripts/run_nested_tool_fixture_pack.py --out-dir benchmarks/results/nested_tool_fixture_pack
python scripts/assert_ci_artifacts.py --results-dir benchmarks/results
```

The `.[test]` extra installs the test runner used by CI. A clean GitHub runner
does not inherit local development packages.

The workflow uploads one downloadable artifact bundle with:

- `benchmarks/results/evidence_pack_ci/` — reviewer-friendly CI evidence pack;
- `benchmarks/results/nested_tool_fixture_pack/` — hard nested tool-call fixture
  pack with good/bad adapted results, good/bad evidence packs, combined report,
  triage, and manifest.

`scripts/assert_ci_artifacts.py` fails CI if required files are missing or if the
manifest classifications drift from `ci`/`fixture` evidence boundaries.

## Recommended Pull Request Rule

Block merge if any of these fail:

1. Python tests fail.
2. `mbs bench` does not produce result JSON.
3. `mbs report --require-traces` exits nonzero.
4. `mbs gate` misses configured thresholds.
5. Nested fixture evidence pack generation fails.
6. CI artifact completeness or manifest-boundary assertions fail.

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

The repository includes `benchmarks/provider_gate.example.yaml` as a starting
point for real provider or OSS model gates. It adds coverage checks so a tiny
run cannot accidentally pass as credible evidence:

- minimum report rows;
- minimum case runs;
- minimum model count;
- minimum schema count;
- trace coverage required;
- zero hidden infra failures.

## Adding A Real Agent Gate

For your own agent, replace `benchmarks/models.yaml` with a config that points to
your schemas and cases, or adapt provider responses first. See
`docs/mbs_provider_recipes.md` for separate text, JSON-mode, and tool-call flows:

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
mbs gate \
  --results benchmarks/results/provider_tool_call.mbs.json \
  --config benchmarks/provider_gate.example.yaml \
  --out benchmarks/results/provider_gate.json
mbs triage --results benchmarks/results/provider_tool_call.mbs.json --out benchmarks/results/provider_triage.json
```

For the hard nested tool-call schema, use the one-command runner. It can reuse a
saved response JSONL or collect from Azure/OpenAI-compatible endpoints before it
builds the classified evidence pack:

```bash
python scripts/run_nested_provider_evidence.py \
  --responses results/provider_nested_tool_call.responses.jsonl \
  --model provider-or-oss-model-id \
  --classification provider \
  --mode tool_call \
  --out-dir results/nested_provider_evidence

python scripts/run_nested_provider_evidence.py \
  --provider openai-compatible \
  --endpoint http://127.0.0.1:8000 \
  --model local-model-id \
  --classification oss \
  --mode tool_call \
  --dry-run \
  --json
```

If this gate fails, inspect `provider_gate.json`, the Markdown report, and the
triage file. A gate failure is useful evidence: it tells you whether the problem
is schema validity, semantic correctness, clean JSON formatting, trace coverage,
run coverage, or infrastructure.

## Evidence Boundary

Use CI output as software/regression evidence. Use real-provider or OSS result
JSON plus reports as model-behavior evidence only when the run design is clear
and failures are not hidden.
