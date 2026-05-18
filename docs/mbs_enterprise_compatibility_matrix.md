# MBS Enterprise Compatibility Matrix

## Status

This matrix records implemented and configured compatibility evidence for MBS v0.1.1. It is a living readiness artifact, not a guarantee that every downstream enterprise environment is supported.

## Runtime support target

| Area | Target | Current evidence | Status |
| --- | --- | --- | --- |
| Python | 3.9+ package metadata | `pyproject.toml` requires `>=3.9`; classifiers include 3.9-3.12 | Targeted |
| Primary local dev runtime | Python 3.11 on Windows | local full suite passes | Verified locally |
| CI runtime | Python 3.11 | GitHub Actions matrix configured | Configured |
| CLI install | editable install and built wheel | local `.audit_venv`, package proof, fresh wheel install proof | Verified locally |
| Package artifacts | sdist and wheel | `scripts/assert_release_package.py` | Verified locally and CI-configured |

## Operating-system proof

| OS | Evidence | Current status |
| --- | --- | --- |
| Windows | Local full pytest, package build, package check, fresh install, artifact classification | Verified locally |
| Ubuntu Linux | GitHub Actions matrix entry `ubuntu-latest` | Configured; remote run evidence pending |
| macOS | GitHub Actions matrix entry `macos-latest` | Configured; remote run evidence pending |

## Release-hygiene compatibility gates

| Gate | Command | Expected status |
| --- | --- | --- |
| Unit/conformance suite | `python -m pytest -q` | PASS |
| Build packages | `python -m build` | PASS |
| Package content inspection | `python scripts/assert_release_package.py --dist-dir dist` | PASS |
| Fresh wheel install | `python scripts/assert_fresh_install.py --dist-dir dist` | PASS |
| Public artifact classification | `python scripts/classify_release_artifacts.py benchmarks/results/sample_benchmark.json benchmarks/results/sample_benchmark.md docs/mbs_evidence_brief.md --repo-root . --fail-on-review` | PASS |
| CI artifact completeness | `python scripts/assert_ci_artifacts.py --results-dir benchmarks/results` | PASS after CI artifact generation |

## Shell considerations

- Windows local execution should use PowerShell-safe commands.
- Provider credentials must remain in environment variables or secret managers.
- Evidence capture should use explicit UTF-8 where scripts write files.
- Release checks should not depend on source checkout importability after wheel install.

## Current limitations

- Remote CI results have not yet been captured in this local workspace.
- Python 3.9, 3.10, and 3.12 are package metadata targets but not yet full matrix proof in CI.
- Enterprise deployment environments still need pilot-specific validation for their OS, Python, shell, secret-management, and provider configuration.
