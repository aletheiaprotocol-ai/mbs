# MBS Security, Privacy, and Release Hygiene

## Status


This document records the first local release-hygiene pass for MBS. It is a product-readiness artifact, not a formal third-party security audit.

## Current guarantees

- MBS core validation is local and deterministic.
- Provider runner scripts expect credentials through environment variables, not committed literals.
- CLI and agent-tool paths now return controlled errors for common malformed file inputs covered by regression tests.
- Generated virtual environments and local result directories are ignored by `.gitignore`.
- The release package includes source, docs, examples, selected benchmark metadata, and selected tests via `MANIFEST.in`.
- `docs/mbs_compliance_security_boundary.md` defines the product-local data, compliance, and external-sharing boundary.
- `scripts/classify_release_artifacts.py` classifies evidence artifacts before external sharing.

## Operator responsibilities

- Store provider credentials in environment variables or a secret manager.
- Do not paste provider keys into YAML, JSON, response fixtures, transcripts, or evidence packs.
- Classify benchmark artifacts before sharing them externally.
- Treat traces and evidence packs as potentially sensitive when they include raw inputs or raw model outputs.
- Use explicit UTF-8 capture for Windows-generated evidence files.

## Files intentionally excluded from release evidence

- Virtual environments: `.audit_venv/`, `.mbs_audit_venv/`, `.clean_install_venv/`, `.venv/`, `external_user_smoke_test/.venv_smoke/`.
- Generated result directories: `results/`, `benchmarks/results/ci_*.json`, `benchmarks/results/ci_*.md`, clean-install outputs.
- Python/build caches: `__pycache__/`, `.pytest_cache/`, `dist/`, `build/`, `*.egg-info/`.

## Credential-scan baseline

The local release-hygiene regression test scans release-relevant source, docs, examples, scripts, tests, workflows, and top-level markdown/config files for high-confidence token patterns:

- OpenAI-style `sk-...` keys;
- Hugging Face `hf_...` tokens;
- GitHub `ghp_...` / related personal access token forms.

The scan deliberately allows environment-variable names such as `AZURE_OPENAI_API_KEY`; these are configuration handles, not secrets.

## Known boundaries

- This is not a penetration test.
- It does not prove absence of all secrets in local ignored files.
- It does not classify provider-generated evidence for public release.
- It does not prove GDPR/HIPAA/SOC 2 compliance.

## Enterprise Pilot blocker disposition

Gate 10 remains partial until:

1. cross-platform CI runs the release-hygiene checks;
2. public evidence artifacts are reviewed for sensitive inputs/outputs;
3. package contents are verified from a built source distribution/wheel in a fresh environment;
4. provider-classified evidence is separated from local fixture evidence.

Current implementation status:

- Package contents are checked by `scripts/assert_release_package.py`.
- Built wheel installability is checked by `scripts/assert_fresh_install.py`.
- Artifact classification is checked by `scripts/classify_release_artifacts.py`.
- The formal local boundary is documented in `docs/mbs_compliance_security_boundary.md`.