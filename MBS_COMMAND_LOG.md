# MBS Command Log

## May 16, 2026 - Windows/BOM Output JSON Fix Validation

**Repository:** `D:\projects\mbs-public-release`  
**Virtualenv Python:** `D:\projects\mbs-public-release\.mbs_audit_venv\Scripts\python.exe`

### 1. Targeted BOM Regression Test

Command:

```powershell
python -m pytest tests/test_mbs_conformance.py::test_cli_validate_supports_output_json_files_with_utf8_bom -q
```

Output:

```text
.                                                                        [100%]
1 passed in 0.11s
```

### 2. Create BOM-Prefixed Invalid Output JSON

Command:

```powershell
python -c "import json; from pathlib import Path; Path('bad_output.json').write_text(json.dumps({'decision':'MANUAL_CHECK','risk_level':'HIGH','human_review_required':'yes','reason':'Looks risky.','extra':'not allowed'}), encoding='utf-8-sig')"
```

### 3. Validate BOM-Prefixed Invalid Output JSON

Command:

```powershell
python -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output bad_output.json
```

Output:

```text
JSON valid: True
Schema valid: False
Status: FAIL
- invented_enum at decision: {'field': 'decision', 'type': 'invented_enum', 'received': 'MANUAL_CHECK', 'allowed': ['APPROVE', 'REVIEW', 'BLOCK', 'ESCALATE']}
- wrong_type at human_review_required: {'field': 'human_review_required', 'type': 'wrong_type', 'expected': 'boolean', 'received': 'str'}
- warning extra_key at extra: {'field': 'extra', 'type': 'extra_key'}
```

Result: No traceback. Controlled validation failure.

### 4. Compile Fintech Schema

Command:

```powershell
python -m mbs.cli compile examples/fintech_transaction_risk/schema.json
```

Output excerpt:

```text
You must respond with a valid JSON object containing the following fields:

- "decision" (required): string -- Transaction decision. Must be one of: APPROVE, REVIEW, BLOCK, ESCALATE
- "risk_level" (required): string -- Risk level. Must be one of: LOW, MEDIUM, HIGH, CRITICAL
- "reason" (required): string -- Reason for the decision
- "human_review_required" (required): boolean -- Whether a human should review

Do not include any text outside the JSON object.

# ~121 tokens (0.0% savings vs verbose)
```

### 5. Validate Known-Good Output

Command:

```powershell
python -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json
```

Output:

```text
JSON valid: True
Schema valid: True
Status: PASS
```

### 6. Validate Normal UTF-8/ASCII Output File

Command:

```powershell
Set-Content -Path normal_output.json -Encoding Ascii -Value '{"decision":"REVIEW","risk_level":"HIGH","reason":"Normal UTF-8/ASCII file still works","human_review_required":false}'
python -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output normal_output.json
```

Output:

```text
JSON valid: True
Schema valid: True
Status: PASS
```

### 7. Validate Inline JSON Behavior

PowerShell direct inline JSON strips double quotes in this shell, so inline behavior was verified through a small Python script in `mbs_product_readiness_audit/check_inline_json.py`.

Command:

```powershell
python mbs_product_readiness_audit\check_inline_json.py
```

Output:

```text
JSON valid: True
Schema valid: True
Status: PASS
```

### 8. Malformed File-Backed JSON Behavior

Command:

```powershell
Set-Content -Path invalid_output.json -Encoding Ascii -Value '{"decision":'
python -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output invalid_output.json
```

Output excerpt:

```text
json.decoder.JSONDecodeError: Expecting value: line 2 column 1 (char 13)
```

Result: Still tracebacks. Documented as follow-up hardening, separate from the fixed BOM issue.

### 9. Targeted Test Files

Command:

```powershell
python -m pytest tests/test_mbs_conformance.py tests/test_mbs_product.py -q
```

Output:

```text
93 passed in 2.79s
```

### 10. Full Test Suite

Command:

```powershell
python -m pytest -q
```

Output:

```text
140 passed, 10 skipped in 3.39s
```

## May 17, 2026 - P0 Productization Execution Slice

**Repository:** `D:\projects\mbs-public-release`  
**Clean audit venv:** `D:\projects\mbs-public-release\.audit_venv\Scripts\python.exe`  
**Verified import paths:**
- `D:\projects\mbs-public-release\mbs\__init__.py`
- `D:\projects\mbs-public-release\mbs\cli.py`

### Clean install and BOM verification

- Created clean editable install in `.audit_venv`.
- Verified `mbs==0.1.1` imports from the release repo, not the `NEXUS` workspace.
- Re-verified BOM-prefixed schema/output files through `validate`.
- Confirmed BOM-safe agent-tool `output_path` validation.

### CLI surface audit

Audited `--help` for `mbs`, `compile`, `validate`, `check`, `trace`, `bench`, `test`, `demo`, `agent-tools`, `report`, `gate`, `evidence-pack`, `compare`, `retry-audit`, `models`, `triage`, `adapt-responses`, and `make-response-template`.

Transcripts saved under `results/session_audit_20260516/cli_surface/`.

### External-user smoke test

```text
Smoke test passed. Transcript: D:\projects\mbs-public-release\external_user_smoke_test\command_transcript.txt
EXIT=0
```

### Hard workflow fixture verification

Verified all three serious workflow fixture packs with good/bad generated MBS result files and gates:

- `examples/incident_response_runbook/`
- `examples/fintech_transaction_risk/`
- `examples/support_ticket_triage/`

```text
incident_response_runbook: good gate exit 0, bad gate exit 2
fintech_transaction_risk: good gate exit 0, bad gate exit 2
support_ticket_triage: good gate exit 0, bad gate exit 2
```

Artifacts saved under `results/session_audit_20260516/hard_fixtures/`.

### Agent workflow proof

```text
Workflow artifacts written to D:\projects\mbs-public-release\examples\agent_workflow_transaction_review\artifacts
EXIT=0
```

### Regression tests

Focused agent/contract tests:

```text
4 passed in 0.15s
```

Full suite:

```text
162 passed, 10 skipped in 4.30s
```

## May 17, 2026 - CLI Command Matrix Closure

Added local command-matrix evidence in `docs/mbs_cli_command_matrix_20260517.md`.

Verified public subcommand `--help` behavior for:

```text
compile, validate, check, trace, cost, bench, demo, test, lang, report, gate,
evidence-pack, compare, retry-audit, models, triage, agent-tools,
adapt-responses, make-response-template
```

All help paths returned exit `0` with no stderr. Regression anchors now include controlled misuse/edge-command matrix tests, BOM artifact-command tests, malformed JSON tests, and CI workflow assertions.

Full suite after CLI edge hardening:

```text
183 passed, 10 skipped in 5.17s
```

Post-change release gates:

```text
MBS release package check: PASS
MBS fresh install check: PASS
MBS artifact classification: PASS
review required: 0
blocking findings: 0
```

## May 17, 2026 - Multi-Schema Fixture Benchmark Breadth Closure

Added `scripts/run_multi_schema_fixture_bundle.py` and `benchmarks/multi_schema_fixture_gate.yaml` to build a local fixture/software benchmark bundle across:

- `examples/incident_response_runbook/`
- `examples/fintech_transaction_risk/`
- `examples/support_ticket_triage/`
- `examples/nested_tool_arguments/`

The bundle writes `benchmarks/results/multi_schema_fixture_bundle/manifest.json`, an evidence pack, raw fixture result files, gate evidence, and a README. It records trace coverage and cost-per-valid-output metrics while explicitly classifying the bundle as `fixture_smoke_not_provider_benchmark`.

Bundle validation:

```text
MBS multi-schema fixture bundle: PASS
Result files: 4
Report rows: 4
Total runs: 49
Traceable case rows: 49
Gate status: PASS
```

Artifact classification:

```text
MBS artifact classification: PASS
- artifacts: 18
- review required: 0
- blocking findings: 0
```

Targeted regression tests:

```text
7 passed in 0.77s
```

Full validation and release gates after CI artifact checker update:

```text
185 passed, 10 skipped in 6.42s
MBS release package check: PASS
MBS fresh install check: PASS
MBS artifact classification: PASS
- artifacts: 21
- review required: 0
- blocking findings: 0
```

B-006 is closed locally for fixture/software benchmark breadth. Provider/OSS breadth and real provider-classified workflow evidence remain separate B-007/B-008 blockers.

## May 16, 2026 - Release Hygiene Slice

### Security and privacy docs

- Added `SECURITY.md` with private vulnerability-reporting guidance, credential-handling policy, data/artifact handling boundary, and readiness boundary.
- Added `docs/mbs_security_privacy_release_hygiene.md` with current guarantees, operator responsibilities, release exclusions, credential-scan baseline, and remaining Gate 10 boundaries.
- Added `SECURITY.md` to `MANIFEST.in` and linked the hygiene doc from `README.md`.

### Credential scan baseline

Scanned release-relevant source/docs/examples/scripts/tests/workflows/config for high-confidence token patterns while excluding generated venvs, results, build outputs, and caches.

Findings:

```text
No committed high-confidence OpenAI, Hugging Face, or GitHub token literal found in release-relevant files.
Environment variable names such as AZURE_OPENAI_API_KEY remain intentionally documented.
```

### Regression tests

Added `tests/test_release_hygiene.py` covering:

- security/hygiene docs exist and define boundaries;
- `.gitignore` excludes audit/smoke venvs and result artifacts;

## May 16, 2026 - Enterprise Readiness Reconciliation

**Repository:** `D:\projects\mbs-public-release`  
**Virtualenv Python:** `D:\projects\mbs-public-release\.audit_venv\Scripts\python.exe`

### Inputs reviewed

- `mbs_enterprise_readiness/ENTERPRISE_READINESS_SCORECARD.md`
- `mbs_enterprise_readiness/RELEASE_BLOCKERS.md`
- `tests/test_mbs_conformance.py`
- `tests/test_mbs_product.py`
- `mbs/validate.py`
- `MBS_FIX_LOG.md`

### Reconciled evidence

- Public CLI success-path matrix regression covers the current command surface locally.
- Validator tests already cover prose-wrapped JSON, fenced Markdown JSON, strict bool/type behavior, nested missing-key paths, and schema-valid safety-review warnings.
- Latest local full validation remains recorded as `177 passed, 10 skipped`, with package check, fresh install check, and artifact classification all passing in the preceding release gate run.

### Boundary retained

- `ENTERPRISE PILOT READY` remains not allowed.
- `ENTERPRISE PRODUCTION READY` remains not allowed.
- Remote CI matrix execution, broader negative/edge command coverage, provider-classified workflow evidence, and formal compliance/security review remain open.

## May 16, 2026 - JSON Robustness Regression Expansion

**Repository:** `D:\projects\mbs-public-release`  
**Virtualenv Python:** `D:\projects\mbs-public-release\.audit_venv\Scripts\python.exe`

### Tests added

- Malformed inline JSON through `mbs validate --json` returns machine-readable `invalid_json` without traceback.
- Malformed fenced Markdown JSON remains a controlled `invalid_json` failure.
- Array/primitive JSON against object schemas fails with top-level `wrong_type`.
- Multiple JSON objects in prose use the first balanced object deterministically and report schema errors on that object.

### Focused validation

```text
29 passed in 0.34s
```

### Full validation

```text
181 passed, 10 skipped in 5.11s
```

### Boundary retained

This improves local validator/CLI robustness only. Standalone script coverage, broader provider raw-output malformed JSON coverage, remote CI matrix evidence, provider-classified runs, and formal compliance/security review remain open.

## May 16, 2026 - Release Gate Rebuild and Artifact Classification Refinement

**Repository:** `D:\projects\mbs-public-release`  
**Virtualenv Python:** `D:\projects\mbs-public-release\.audit_venv\Scripts\python.exe`

### First gate attempt

- Package check: `PASS`.
- Fresh install: `PASS`.
- Artifact classification: `REVIEW` because `README.md` was `unknown` and `SECURITY.md` contained a public contact email.

### Fix applied

- Classified expected root release docs as `docs`.
- Suppressed only the public contact-email finding for `SECURITY.md`.
- Added classifier regression coverage for public release docs.

### Final validation

```text
182 passed, 10 skipped in 5.42s
MBS release package check: PASS
MBS fresh install check: PASS
MBS artifact classification: PASS
- artifacts: 7
- review required: 0
- blocking findings: 0
```

### Boundary retained

The passing classification gate applies to the selected public release artifacts only. Provider/OSS/HPC artifacts, unknown files, and sensitive raw outputs still require review; remote CI matrix evidence and formal third-party review remain open.
- release-relevant text files contain no high-confidence provider/GitHub token literals.

Focused validation:

```text
3 passed in 0.50s
```

## May 16, 2026 - Release Package Proof Slice

### Package inspector

- Added `scripts/assert_release_package.py` to inspect built `dist/*.tar.gz` and `dist/*.whl` artifacts.
- The inspector verifies required release metadata/docs/tests, metadata presence, console entry point metadata, and absence of forbidden local artifacts such as virtualenvs, caches, generated results, and `mbs_product_readiness_audit/`.

### Package boundary fix

- Updated `pyproject.toml` to exclude `mbs_product_readiness_audit*` from package discovery.
- Updated `MANIFEST.in` to prune `mbs_product_readiness_audit` from source distributions while still including security docs, hygiene docs, release tests, scripts, examples, and deterministic sample benchmark artifacts.

### Validation

Focused package tests:

```text
3 passed in 0.18s
```

Rebuilt packages and verified package contents:

```text
Successfully built mbs-0.1.1.tar.gz and mbs-0.1.1-py3-none-any.whl
assert_release_package.py: PASS
wheel file_count: 28
sdist file_count: 187
```

### CI package gate

- Added package-build tooling install to `.github/workflows/mbs-ci.yml`.
- Added CI steps to run `python -m build` and `python scripts/assert_release_package.py --dist-dir dist` before demo/evidence artifact generation.
- Updated README CI commands to include package build and package content inspection.

Targeted release checks after the CI update:

```text
6 passed in 0.62s
MBS release package check: PASS
```

Full local validation after package proof changes:

```text
168 passed, 10 skipped in 5.05s
```

## May 16, 2026 - Fresh Wheel Install Proof Slice

### Fresh install proof

- Added `scripts/assert_fresh_install.py`.
- The script creates a temporary virtual environment, installs the built wheel from `dist/`, removes `PYTHONPATH`, then runs import, `mbs --help`, and `mbs validate` checks from outside the source checkout.
- Added `tests/test_fresh_install.py` for manifest/script coverage and deterministic wheel selection behavior.

### CI update

- Added `python scripts/assert_fresh_install.py --dist-dir dist` to `.github/workflows/mbs-ci.yml` after package-content inspection.
- Updated README CI commands to include fresh wheel install proof.

### Validation

```text
Focused release/install tests: 8 passed in 0.66s
MBS release package check: PASS
MBS fresh install check: PASS
```

## May 16, 2026 - Artifact Classification, Compliance Boundary, and Cross-Platform CI Slice

### Artifact classification

- Added `scripts/classify_release_artifacts.py`.
- The classifier assigns each artifact an evidence class, sensitivity, sharing boundary, and review requirement.
- It blocks high-confidence secrets, flags provider/OSS/HPC evidence for review, and allows public fixture/sample/CI artifacts only within a software-evidence boundary.
- Added `tests/test_artifact_classification.py` covering public fixture artifacts, provider-review artifacts, and blocking secret findings.

### Compliance/security boundary

- Added `docs/mbs_compliance_security_boundary.md` defining product scope, data classes, security controls, operator responsibilities, non-goals, and minimum release commands.
- Updated `docs/mbs_security_privacy_release_hygiene.md` and `README.md` to reference the boundary and classifier.

### Cross-platform CI configuration

- Updated `.github/workflows/mbs-ci.yml` to run the structured-output regression gate on `ubuntu-latest`, `windows-latest`, and `macos-latest` with Python 3.11.
- Added artifact classification as a CI release gate with `--fail-on-review` for public CI artifacts.
- CI artifact uploads now include OS/Python in artifact names.

### Validation

```text
Focused release/compliance tests: 11 passed in 0.71s
Full repository suite: 173 passed, 10 skipped in 5.14s
MBS release package check: PASS
MBS fresh install check: PASS
MBS artifact classification: PASS
```

## May 16, 2026 - CI Workflow Assertions, Compatibility Matrix, and Release Checklist Slice

### CI workflow regression guard

- Added `tests/test_ci_release_workflow.py` to assert the GitHub Actions release workflow remains cross-platform.
- The test guards the Ubuntu/Windows/macOS matrix, Python 3.11 runtime, release package build, fresh install proof, artifact classification gate, CI artifact assertion, and matrix-scoped artifact upload names.

### Enterprise compatibility and release checklist docs

- Added `docs/mbs_enterprise_compatibility_matrix.md` documenting current runtime support targets, OS proof, release gates, shell considerations, and explicit limitations.
- Added `docs/mbs_release_readiness_checklist.md` with operator-facing release commands, checklist items, evidence classification rules, and allowed/not-allowed release language.
- Linked both docs from `README.md`.

### Package integration

- Added `tests/test_ci_release_workflow.py` to `MANIFEST.in`.
- Added the compatibility matrix, release checklist, and CI workflow test to `scripts/assert_release_package.py` required source-distribution content.
- Updated `tests/test_release_package.py` fixture contents to match the stricter package requirement.

### Validation

Initial validation found the package fixture needed the new required files. After updating the fixture, validation passed:

```text
Successfully built mbs-0.1.1.tar.gz and mbs-0.1.1-py3-none-any.whl
Full repository suite: 176 passed, 10 skipped in 4.76s
MBS release package check: PASS
MBS fresh install check: PASS
MBS artifact classification: PASS
```

## May 16, 2026 - Enterprise Blocker Disposition Slice

- Added `docs/mbs_enterprise_blocker_disposition.md` with owner/severity/target/evidence/verification/status/closure fields for every remaining Enterprise Pilot and Production blocker.
- Linked the disposition doc from `README.md`.
- Added the disposition doc to `scripts/assert_release_package.py` required source-distribution contents and updated release package fixture expectations.
- Expanded public CLI success-path regression coverage across all major subcommands.

## May 17, 2026 - Final Release Gate Rerun and Remote CI Evidence Check

**Repository:** `D:\projects\mbs-public-release`  
**Virtualenv Python:** `D:\projects\mbs-public-release\.audit_venv\Scripts\python.exe`

### Final local release gates

- Inspected final repository state and confirmed package-included files changed after the prior build, so release artifacts needed a fresh rebuild and gate pass.
- Rebuilt `dist/mbs-0.1.1.tar.gz` and `dist/mbs-0.1.1-py3-none-any.whl`.
- Full local repository suite passed again: `182 passed, 10 skipped in 5.14s`.
- Package inspector passed for both wheel and sdist.
- A combined first run reported a transient fresh-install failure: `[WinError 267] The directory name is invalid`.
- Immediate diagnostic rerun of `scripts/assert_fresh_install.py --dist-dir dist --json --keep-venv` passed, including import, installed `mbs --help`, and installed `mbs validate --json` checks from the built wheel.
- Final chained release gate rerun passed:

```text
MBS release package check: PASS
- wheel dist\mbs-0.1.1-py3-none-any.whl: PASS
- sdist dist\mbs-0.1.1.tar.gz: PASS
MBS fresh install check: PASS
- wheel: dist\mbs-0.1.1-py3-none-any.whl
MBS artifact classification: PASS
- artifacts: 7
- review required: 0
- blocking findings: 0
```

### Remote CI status

- GitHub remote: `https://github.com/aletheiaprotocol-ai/mbs.git`, branch `main`.
- `gh` CLI is authenticated for `aletheiaprotocol-ai` with `repo` and `workflow` scopes.
- Latest inspected remote MBS CI run: `https://github.com/aletheiaprotocol-ai/mbs/actions/runs/25870490537`, created `2026-05-14T15:59:37Z`, conclusion `success`.
- That run contained only one job, `Structured-output regression gate`; it is not evidence for the current local three-OS matrix.
- Remote cross-platform matrix evidence remains open until the current workflow changes are pushed and a new GitHub Actions matrix run completes successfully.
