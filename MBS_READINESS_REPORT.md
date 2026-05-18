# MBS Readiness Report

## Product Readiness Audit Status

**Date:** May 16, 2026  
**Repository:** `D:\projects\mbs-public-release`  
**Environment:** `D:\projects\mbs-public-release\.mbs_audit_venv`  
**Python:** 3.11.9

## Current Status

**Local release hygiene, CLI robustness, agent-tool contract, and fixture benchmark breadth checks passed with boundary notes.** Core package install, import, CLI smoke tests, package gates, artifact classification, malformed JSON handling, BOM handling, versioned agent-tool envelopes, multi-schema fixture benchmark evidence, and pytest suite pass locally. Remote non-Windows CI evidence, provider/OSS breadth evidence, real provider-classified workflow runs, and formal third-party compliance/security review remain separate Enterprise Pilot blockers.

## Fixed in This Audit

### Windows / UTF-8 BOM JSON Handling

**Status:** Fixed

MBS now handles UTF-8 BOM-prefixed JSON for:

- Schema files via `mbs.compiler.load_schema()` using `encoding="utf-8-sig"`
- Output JSON files via `mbs.cli._load_json_or_inline()` using `encoding="utf-8-sig"`

The manual invalid-output test now returns a controlled validation result instead of a traceback:

```text
JSON valid: True
Schema valid: False
Status: FAIL
- invented_enum at decision
- wrong_type at human_review_required
- warning extra_key at extra
```

## Verified Commands

```powershell
python -m mbs.cli compile examples/fintech_transaction_risk/schema.json
python -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json
python -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output bad_output.json
python -m pytest tests/test_mbs_conformance.py tests/test_mbs_product.py -q
python -m pytest -q
```

## Test Results

```text
tests/test_mbs_conformance.py tests/test_mbs_product.py: 93 passed
Full suite: 140 passed, 10 skipped
```

## Closed Local Follow-ups

### Malformed file-backed JSON

Malformed file-backed JSON is now routed through controlled CLI input handling or machine-readable invalid-JSON validation payloads, depending on command semantics. Regression tests cover inline JSON, file JSON, JSONL records, config files, request files, BOM inputs, and public edge-command paths without Python tracebacks.

### CLI command matrix

The public CLI command matrix is documented in `docs/mbs_cli_command_matrix_20260517.md`. All public subcommands have help-path verification plus success/failure regression anchors.

### Multi-schema fixture benchmark breadth

`scripts/run_multi_schema_fixture_bundle.py` builds a local four-schema fixture benchmark bundle covering incident response, fintech transaction risk, support ticket triage, and nested tool arguments. The bundle includes trace coverage, cost-per-valid-output metrics, an evidence pack, gate result, and classification manifest. This closes B-006 locally as fixture/software evidence only; provider/OSS evidence remains tracked under B-007/B-008.

### Adversarial hard-schema fixture pack

`examples/adversarial_policy_execution/` and `scripts/run_adversarial_hard_schema_pack.py` add a strict B-004 adversarial fixture pack beyond the existing incident, fintech, support, and nested-tool examples. The schema uses nested `additionalProperties: false`, enums, consts, arrays, numeric bounds, string length limits, source-id patterns, target patterns, and unsafe-text review warnings.

The generated evidence bundle at `benchmarks/results/adversarial_hard_schema_pack/manifest.json` passed with:

- Good fixture rows: `8`, schema-valid rate `1.0`, semantic-correct rate `1.0`.
- Bad fixture rows: `8`, fail/review rows `8`, schema-valid rate `0.125`, semantic-correct rate `0.0`.
- Traceable case rows: `16`; missing trace rows: `0`.
- Expected failure coverage: `invalid_enum`, `invented_enum`, `above_maximum`, `wrong_type`, `const_mismatch`, `extra_key`, `too_few_items`, `pattern_mismatch`, `missing_required_key`, `safety_review_required`, and `semantic_mismatch`.

This closes B-004 locally as hard software/fixture evidence. It does not replace provider/OSS breadth evidence, real provider-classified workflow runs, remote CI evidence, or governance review.

### Agent-tool contract

The transport-neutral agent tool surface is documented in `docs/mbs_agent_tool_contract_v1.md`. Tool descriptors include `contract_version: mbs-agent-tools/v1` and `stability: stable`; JSON CLI calls return stable success and controlled error envelopes without tracebacks. This closes B-005 locally; remote CI evidence remains tracked separately.

### Hard local validation pass — 2026-05-17

The local validation pass was expanded beyond targeted blocker tests:

- Full test suite: `186 passed, 10 skipped`.
- Fresh release build: `mbs-0.1.1.tar.gz` and `mbs-0.1.1-py3-none-any.whl` built successfully.
- Release package gate: `PASS` for both sdist and wheel, with no missing required files or forbidden packaged paths.
- Fresh wheel install gate: `PASS`; clean temporary environment installed `mbs-0.1.1`, imported `mbs.__version__`, loaded the CLI, and validated the fintech fixture.
- Multi-schema fixture benchmark: `PASS`; 4 workflows, 4 schemas, 4 models, 49 total runs, 49 traceable case rows, 0 missing traces, gate `PASS`, and cost-per-valid-output present.
- CI artifact completeness gate: `PASS`; required files present, CI gate `PASS`, nested fixture evidence `PASS`, and multi-schema evidence `PASS`.

Boundary: this is hard local software/fixture evidence. It still does not replace remote OS matrix evidence, live provider evidence, or third-party governance/security review.

## Readiness Decision

MBS is improved and the Windows/BOM output JSON handling bug plus malformed/edge CLI input handling are locally hardened. Do not claim Enterprise Pilot Ready until remote Ubuntu/Windows/macOS CI run evidence and required governance review evidence are attached.
