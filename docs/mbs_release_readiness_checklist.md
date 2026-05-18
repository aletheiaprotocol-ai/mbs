# MBS Release Readiness Checklist

## Status

This checklist is the operator-facing release gate for MBS v0.1.1. It consolidates local tests, package proof, artifact classification, and compatibility evidence. Passing it supports a release-hygiene claim; it does not replace legal, security, procurement, or enterprise pilot review.

## Required pre-release commands

Run from the repository root:

```bash
python -m pip install -e ".[test]"
python -m pip install build
python -m pytest -q
python -m build
python scripts/assert_release_package.py --dist-dir dist
python scripts/assert_fresh_install.py --dist-dir dist
python scripts/classify_release_artifacts.py benchmarks/results/sample_benchmark.json benchmarks/results/sample_benchmark.md docs/mbs_evidence_brief.md --repo-root . --fail-on-review
python scripts/run_nested_provider_evidence.py --model readiness-dry-run --classification oss --mode tool_call --out-dir benchmarks/results/nested_provider_dry_run --dry-run --json
python scripts/run_nested_provider_evidence.py --model llama3.2:1b --classification oss --mode tool_call --runner ollama --out-dir benchmarks/results/nested_ollama_dry_run --dry-run --json
python scripts/run_nested_provider_evidence.py --model local-model --classification oss --mode json_mode --runner lm-studio --out-dir benchmarks/results/nested_lm_studio_dry_run --dry-run --json
```

## Checklist

| Item | Evidence | Required result |
| --- | --- | --- |
| Tests pass | full pytest output | no failures |
| Package builds | `dist/*.tar.gz`, `dist/*.whl` | both artifacts created |
| Package content is clean | `assert_release_package.py` | PASS |
| Wheel installs from scratch | `assert_fresh_install.py` | PASS |
| Public artifacts are classified | `classify_release_artifacts.py --fail-on-review` | PASS |
| Provider evidence scaffold is safe | `run_nested_provider_evidence.py --dry-run`, `run_nested_provider_evidence.py --dry-run --runner ollama`, `run_nested_provider_evidence.py --dry-run --runner lm-studio`, plus `tests/test_nested_provider_evidence.py` | no live provider call, no secret access, template/manifest written |
| Token scan passes | `tests/test_release_hygiene.py` | no high-confidence tokens |
| CI matrix configured | `.github/workflows/mbs-ci.yml` | Ubuntu, Windows, macOS |
| Compatibility boundaries documented | `docs/mbs_enterprise_compatibility_matrix.md` | present |
| Compliance boundary documented | `docs/mbs_compliance_security_boundary.md` | present |

## Evidence classification rules

- `demo`, `ci`, `fixture`, `docs`, and `sample` artifacts can be public only as software/demo evidence.
- `provider`, `oss`, and `hpc` artifacts require manual review before external sharing.
- Any secret-like finding blocks sharing until the artifact is regenerated and any exposed credential is rotated.
- Dry-run provider evidence plans and fixture response reuse are scaffolding/software evidence only; they do not close real provider/OSS/HPC evidence blockers.

## Release decision language

Allowed if all required checks pass:

- "release hygiene checks passed locally"
- "package build and fresh install proof passed locally"
- "CI is configured for Ubuntu, Windows, and macOS"

Not allowed without additional evidence:

- "Enterprise Pilot Ready"
- "Enterprise Production Ready"
- "compliance certified"
- "all provider evidence public-safe"

## Sign-off fields

- Release candidate:
- Date:
- Operator:
- Full test result:
- Package check result:
- Fresh install result:
- Artifact classification result:
- CI run URL:
- Manual review notes:
