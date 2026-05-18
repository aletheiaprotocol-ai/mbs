# MBS Fix Log

## May 16, 2026 - UTF-8 BOM Output JSON Handling

### Problem
CLI output JSON loader crashed when parsing UTF-8 BOM-encoded JSON files created by Windows PowerShell.

### Root Cause
`_load_json_or_inline()` in `mbs/cli.py` line 606 used `encoding="utf-8"` instead of `encoding="utf-8-sig"` when reading JSON files from disk.

### Solution

#### 1. Fixed `mbs/cli.py` - `_load_json_or_inline()` function

**Before:**
```python
def _load_json_or_inline(value: str) -> Any:
    p = Path(value)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
```

**After:**
```python
def _load_json_or_inline(value: str) -> Any:
    p = Path(value)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
```

**Change:** Line 608 - replaced `encoding="utf-8"` with `encoding="utf-8-sig"`

**Impact:** File reading now strips UTF-8 BOM if present. Inline JSON parsing unaffected.

#### 2. Added Regression Tests

**File:** `tests/test_mbs_conformance.py`
- **Test:** `test_cli_validate_supports_output_json_files_with_utf8_bom()`
- **Purpose:** Exercise the real CLI `validate` command with the real fintech example schema and a BOM-prefixed output JSON file.
- **Coverage:** Confirms `main(["validate", ...])` returns controlled validation failure status `2` and prints `JSON valid: True`, `Schema valid: False`, `Status: FAIL`, plus decision enum, boolean type, and extra-key findings.

### Validation

#### Manual Tests (May 16, 2026)
```
✅ Test 1: BOM output file with invalid data
  Command: mbs validate --schema examples/fintech_transaction_risk/schema.json --output bad_output.json
  Result: No crash. Returns controlled failure with specific validation errors:
    - invented_enum at decision
    - wrong_type at human_review_required  
    - warning extra_key at extra

✅ Test 2: Standard compile
  Command: mbs compile examples/fintech_transaction_risk/schema.json
  Result: Works as expected

✅ Test 3: Good output validation
  Command: mbs validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json
  Result: PASS
```

#### Regression Test Results
```
Targeted: 93 passed
Full:     140 passed, 10 skipped

Test added:
  - tests/test_mbs_conformance.py::test_cli_validate_supports_output_json_files_with_utf8_bom
```

### Follow-up Hardening

Malformed file-backed JSON still raises `json.decoder.JSONDecodeError` with a traceback. This is separate from the BOM bug because syntactically valid BOM-prefixed JSON now loads and validates correctly. See `MBS_FAILURE_LOG.md` for the follow-up task.

### Related Fixes

This fix complements the earlier schema loading fix from the same audit:
- **Schema loading:** `mbs/compiler.py` - `load_schema()` - Changed to `encoding="utf-8-sig"` ✅
- **Output loading:** `mbs/cli.py` - `_load_json_or_inline()` - Changed to `encoding="utf-8-sig"` ✅

### Compatibility

- **UTF-8 without BOM:** Still supported (BOM-sig codec strips BOM if not present)
- **Inline JSON:** Unaffected (BOM handling only applies to file reads)
- **Non-Windows platforms:** No regression (BOM handling works on all platforms)

### Status

**Resolved** - All tests pass, manual validation confirms proper error handling

## May 17, 2026 - P0 Productization Fixes

### Controlled CLI input errors

- Wrapped CLI schema loading with controlled `MBS input error` behavior.
- Missing schema files, invalid schema JSON, non-object schemas, missing output paths, invalid file-backed JSON, invalid records files, and malformed config inputs now fail without Python tracebacks in covered paths.
- Added path-like detection so a missing `*.json`/`*.jsonl` output is not silently treated as inline JSON.

### Agent-tool output path support

- Added `output_path` support to JSON-callable agent tools for `mbs.validate`, `mbs.check`, and `mbs.trace`.
- Reads output files using `utf-8-sig`, preserving Windows BOM compatibility.
- Missing schema/output paths now return controlled agent-tool errors.

### Agent/API contract alignment

- Added stable top-level fields to the Python `check()` result used by agent tools: `failure_reason`, `trace_id`, `schema_hash`, and `contract_hash`.
- This aligns the agent-callable API with the CLI JSON contract and makes failure routing machine-readable.

### Agent workflow proof

- Added `examples/agent_workflow_transaction_review/` with strict schema, good/bad candidate outputs, JSON-callable agent tool requests, and a replay script.
- Added regression coverage proving PASS/FAIL validation, trace creation, and agent-tool `output_path` behavior.

### Validation

```text
Focused agent/contract tests: 4 passed
Full repository suite: 162 passed, 10 skipped
```

## May 16, 2026 - Release Hygiene Fixes

### Security policy and privacy boundary

- Added `SECURITY.md` for private vulnerability reporting, credential handling, artifact sensitivity, and current readiness boundaries.
- Added `docs/mbs_security_privacy_release_hygiene.md` to document local security/privacy/release hygiene guarantees and explicit non-guarantees.

### Release package metadata

- Added `SECURITY.md` to `MANIFEST.in` so security guidance is included in source distributions.
- Added the hygiene document to the README docs index.

### Secret-regression guard

- Added `tests/test_release_hygiene.py` to scan release-relevant text files for high-confidence OpenAI, Hugging Face, and GitHub token formats while excluding generated environments and result artifacts.

### Validation

```text
Focused release-hygiene tests: 3 passed
```

## May 16, 2026 - Release Package Boundary Fixes

### Package inspector

- Added `scripts/assert_release_package.py` to validate built wheel/source-distribution contents.
- Added checks for required docs, required source files, selected tests, metadata files, entry point metadata, and forbidden local artifact paths.

### Audit tooling exclusion

- Excluded `mbs_product_readiness_audit*` from package discovery in `pyproject.toml`.
- Added `prune mbs_product_readiness_audit` to `MANIFEST.in` so local readiness audit tools are not shipped as importable package code.

### Validation

```text
Focused release package tests: 3 passed
Rebuilt dist artifacts: assert_release_package.py PASS
```

### CI gate

- Added package build and release package inspection to GitHub Actions before artifact-generation steps.
- Updated README CI snippet to include `python -m build` and `scripts/assert_release_package.py`.
- Revalidated focused release tests plus package inspector after CI edits.

## May 16, 2026 - Fresh Install Proof

- Added `scripts/assert_fresh_install.py` to prove the built wheel installs and runs from a temporary clean virtual environment.
- The proof exercises import, console entry point help, and fixture-backed `mbs validate --json` without relying on the source checkout being importable.
- Added focused tests for script packaging and deterministic wheel selection.
- Added the fresh-install proof to CI and README CI instructions.

## May 16, 2026 - Artifact Classification and Compliance Boundary

- Added `scripts/classify_release_artifacts.py` to classify artifacts before external sharing.
- The classifier separates public demo/CI/fixture/sample artifacts from provider/OSS/HPC evidence that requires manual review.
- Secret-like findings are blocking; sensitive text findings are restricted; provider/OSS/HPC benchmark artifacts require owner review before sharing.
- Added `docs/mbs_compliance_security_boundary.md` with explicit product scope, data classes, security controls, operator responsibilities, non-goals, and release commands.
- Expanded the GitHub Actions workflow to Ubuntu, Windows, and macOS and added artifact classification as a cross-platform CI gate.
- Validation: `173 passed, 10 skipped`; package check `PASS`; fresh install check `PASS`; artifact classification `PASS` for public sample artifacts.

## May 16, 2026 - CI Workflow Assertion and Release Readiness Documentation

- Added `tests/test_ci_release_workflow.py` to prevent accidental removal of the three-OS CI matrix or release gates.
- Added `docs/mbs_enterprise_compatibility_matrix.md` documenting current Windows local proof, configured Ubuntu/macOS CI proof, Python/runtime support targets, and limitations.
- Added `docs/mbs_release_readiness_checklist.md` with required release commands, classification rules, and safe release-claim language.
- Wired the new test into `MANIFEST.in` and release package inspection.
- Wired the new docs into `README.md` and release package inspection.
- Updated release package fixture tests for the stricter sdist content contract.
- Validation: `176 passed, 10 skipped`; package check `PASS`; fresh install check `PASS`; artifact classification `PASS` for public sample artifacts.

## May 16, 2026 - Enterprise Blocker Disposition

- Added `docs/mbs_enterprise_blocker_disposition.md` to assign remaining readiness blockers to owners, severities, target labels, planned evidence artifacts, verification commands, status, and closure conditions.
- Added the blocker disposition doc to `README.md` and release package inspection requirements.
- Added a broad public CLI success-path command matrix regression covering compile, validate, check, trace, cost, bench, demo, test, lang, report, gate, evidence-pack, compare, retry-audit, models, triage, agent-tools, adapt-responses, and make-response-template.

## May 16, 2026 - Readiness Record Reconciliation

- Updated `mbs_enterprise_readiness/ENTERPRISE_READINESS_SCORECARD.md` so Gate 2 reflects local public CLI success-path matrix coverage instead of the stale “full command matrix missing” wording.
- Updated Gate 3 language to record existing prose-wrapped JSON, fenced JSON, strict bool/type, and safety-review validator coverage while keeping deeper inline/ambiguous JSON coverage open.
- Updated Gate 9 local validation evidence from `176 passed, 10 skipped` to `177 passed, 10 skipped`.
- Updated `mbs_enterprise_readiness/RELEASE_BLOCKERS.md` to keep remaining blockers precise: negative/edge command coverage, remote CI evidence, provider-classified runs, and formal compliance review remain open.

## May 16, 2026 - JSON Robustness Regression Expansion

- Added `tests/test_mbs_conformance.py::test_cli_validate_malformed_inline_json_emits_machine_readable_failure` to prove public CLI malformed inline JSON returns structured `invalid_json` output without traceback.
- Added malformed fenced JSON coverage to ensure broken Markdown fences stay controlled `invalid_json` failures instead of partial extraction.
- Added non-object JSON coverage for arrays/primitives against object schemas, preserving clean `wrong_type` failure reasons.
- Added deterministic multi-object prose coverage so the validator documents first-balanced-object extraction instead of silently choosing a later corrected object.
- Validation: focused conformance `29 passed`; full local suite `181 passed, 10 skipped`.

## May 16, 2026 - Public Artifact Classification Gate Refinement

- Updated `scripts/classify_release_artifacts.py` to classify expected public release docs (`README.md`, `SECURITY.md`, `LICENSE`, `MANIFEST.in`, `pyproject.toml`) as `docs` instead of `unknown`.
- Added a narrow `SECURITY.md` exception so the public vulnerability-reporting contact email does not force restricted classification.
- Kept conservative behavior for secrets, provider/OSS/HPC outputs, unknown files, and sensitive raw artifacts.
- Added `tests/test_artifact_classification.py::test_public_release_docs_are_classified_without_manual_review`.
- Rebuilt `dist` after script/test changes.
- Validation: artifact classifier tests `4 passed`; full local suite `182 passed, 10 skipped`; package check `PASS`; fresh install `PASS`; public artifact classification `PASS` with `0` review-required and `0` blocking findings.
