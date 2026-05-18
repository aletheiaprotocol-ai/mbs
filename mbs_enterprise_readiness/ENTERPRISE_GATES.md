# MBS Enterprise Gates

## Gate 1 — Install and Developer Experience

Required:
- Fresh install on Windows, Linux, and macOS where available.
- Quickstart works without hidden path dependencies.
- No wrong-repo imports.
- `pyproject.toml`/package metadata complete.
- Docs match actual commands.

Current status: **PARTIAL PASS**. Windows audited. Linux/macOS fresh installs still required.

## Gate 2 — CLI Product Surface

Required commands:
- `compile`
- `validate`
- `check`
- `trace`
- `bench`
- `test`
- `agent-tools` or equivalent JSON-callable interface
- `demo`

Required behavior:
- clear help text;
- controlled errors for normal user mistakes;
- machine-readable JSON output where expected;
- no traceback for routine invalid input.

Current status: **PARTIAL PASS**. Main audited paths pass; complete command matrix and negative-case CLI tests are still required.

## Gate 3 — JSON Robustness

Required:
- UTF-8 and UTF-8 BOM input.
- Windows-created JSON.
- Inline JSON.
- File JSON.
- Invalid JSON controlled errors.
- Schema/output file consistency.
- BOM and encoding tests for both request input and output artifact reads.

Current status: **PARTIAL PASS**. BOM request handling was fixed and tested for audited path. Full JSON robustness matrix remains required.

## Gate 4 — Validation Correctness

Required detection:
- invalid JSON;
- schema failure;
- enum failure;
- wrong type;
- missing required fields;
- extra fields;
- nested failures;
- arrays;
- semantic mismatch where semantic checking is enabled.

Current status: **PARTIAL PASS**. Core validation works in audited tests; hard-schema and adversarial validation coverage must expand.

## Gate 5 — Agent Usability

Required callable surfaces:
- CLI with machine-readable output;
- Python API;
- JSON-callable tool interface;
- MCP-style or equivalent wrapper if implemented.

Required output fields:
- `PASS` / `FAIL` / `REVIEW`;
- machine-readable status;
- failure reasons;
- trace ID;
- retry recommendation;
- schema hash / contract hash where available.

Current status: **PARTIAL PASS**. Agent-callable interfaces exist for audited paths; output contract completeness must be hardened.

## Gate 6 — Benchmark Credibility

Required:
- broad, repeatable, honest benchmarks;
- no cherry-picking;
- known failures shown;
- weak models included;
- row-level regressions reported;
- infra failures separated from real model behavior;
- software bugs and benchmark design issues separately classified.

Current status: **PARTIAL PASS**. Current evidence is honest but narrow.

## Gate 7 — Provider and OSS Coverage

Required:
- closed/provider models;
- open/local/HPC models;
- text mode;
- JSON mode;
- tool/function call mode;
- MBS contract + text;
- MBS contract + JSON mode;
- MBS contract + tool calling.

Current status: **FAIL for enterprise**. Azure `gpt-5.5` evidence exists. Broad provider/OSS matrix is missing.

## Gate 8 — Real Workflow Readiness

Required replayable demos/tests for at least three serious workflows:
1. incident response/runbook review;
2. fintech/support/compliance workflow;
3. QME/medical-legal or source-grounded review.

Each must include:
- good case;
- bad case;
- ambiguous case;
- adversarial case;
- audit/trace output.

Current status: **FAIL for enterprise**. Serious workflow packs must be created and tested.

## Gate 9 — CI and Regression

Required:
- MBS usable as a CI gate;
- regression detection in structured-output behavior;
- clear threshold failures;
- no `NO_MATCH` false pass;
- no silent empty-result pass;
- row-level diff reports.

Current status: **PARTIAL PASS**. CI artifact assertion exists. Broader regression matrix and false-pass guards must be hardened.

## Gate 10 — Security and Release Hygiene

Required:
- no secrets in repo;
- no unsafe public test data;
- no accidental huge files;
- clear license;
- clear disclaimers;
- clear limitations;
- safe hosted demo boundaries;
- no overclaiming universal safety;
- dependency/license scan;
- artifact redaction policy.

Current status: **UNKNOWN/PARTIAL**. Formal release hygiene audit is required before paid or enterprise usage.