# Enterprise Readiness Scorecard

## Current score

| Gate | Status | Evidence | Enterprise blocker |
|---|---|---|---|
| Gate 1 — Install/DX | Pass for current software/CI scope | Clean Windows audit venv verified again on 2026-05-18; fresh wheel install proof passes locally; GitHub Actions matrix run `26011688420` passed on Ubuntu, Windows, and macOS; downloaded artifacts validate as `PASS` in `benchmarks/results/remote_ci_matrix_evidence_26011688420.json`; CI records non-secret environment manifests; compatibility matrix documented | Customer-environment validation still separate |
| Gate 2 — CLI surface | Partial pass, improved | Core audited commands plus controlled-error regression coverage for common misuse; CLI help transcripts saved; public CLI success-path matrix regression covers the current command surface locally; P0 focused pack re-verified `130 passed` | Broader negative/edge command matrix and remote cross-platform execution evidence still missing |
| Gate 3 — JSON robustness | Partial pass, improved | BOM request/schema/output paths re-verified; validate/cost/report/gate/adapt-responses/compare/triage/retry-audit/evidence-pack BOM regression tests pass; invalid config/records/schema/output failures are controlled; prose-wrapped JSON, fenced JSON, malformed inline/fenced JSON, non-object JSON, deterministic multi-object prose extraction, strict bool/type checks, and safety-review warnings covered in validator/CLI tests; high-use provider/evidence/tuning scripts patched | Deeper standalone script matrix and broader provider/raw-output malformed JSON matrix still need coverage |
| Gate 4 — Validation correctness | Partial pass, improved | Core tests pass; incident-response, fintech, support-triage, transaction-review, and adversarial nested fixtures cover enums, consts, bounds, required nested fields, extra-key rejection, semantic checks, and unsafe-text review behavior | More hard schemas and real provider adversarial evidence missing |
| Gate 5 — Agent usability | Partial pass, improved | Python/CLI callable paths; `validate`/`check` JSON contract fields covered; agent-tool `output_path` supported; external-user smoke flow and transaction-review agent workflow replay pass | Full enterprise output contract still incomplete |
| Gate 6 — Benchmark credibility | Partial pass, improved | Honest scoped Azure/CI evidence; nested Azure Sweden `gpt-5.5` tool-call run: 25 runs, 0 infra failures, schema-valid 1.0000, semantic-correct 0.8800, gate PASS | Broad repeated matrix missing |
| Gate 7 — Provider/OSS coverage | Fail for enterprise, improved locally | Azure `gpt-5.5` scoped nested-tool evidence; live Leonardo HF-local `hpc` evidence for TinyLlama, Qwen 0.5B/1.5B/3B/7B/14B, Mistral 7B/Nemo, DeepSeek-Qwen 7B/14B, Yi, Granite, Phi, OLMo, Gemma, SmolLM, and 70B Llama families; `bitsandbytes` installed/GPU-verified; 70B 4-bit job `41800766` and compact single-model 70B job `41807878` completed as behavior evidence; compact Qwen/Yi comparison collected; standard MBS replay cross-check generated 339 traceable runs | Current Leonardo runs failed gate thresholds; 70B compact multi-model row was infra-only; additional OSS/HPC families and broader closed-provider matrix missing |
| Gate 8 — Real workflows | Partial pass for software fixtures, fail for enterprise | Incident-response/runbook, fintech transaction-risk, support ticket triage, and transaction-review agent workflow packs with pass/fail fixtures, gates/traces, and safety/adversarial cases; one separate nested-tool Azure provider run exists; serious-workflow provider evidence orchestrator and dry-run request manifest now exist | Need real provider-classified runs for the serious workflow packs before enterprise readiness claims |
| Gate 9 — CI/regression | Pass for current software/CI scope | Full local repository suite passes: `215 passed, 10 skipped`; focused P0 pack passes: `130 passed`; GitHub Actions matrix run `26011688420` passed on Ubuntu, Windows, and macOS; downloaded artifacts validate as `PASS`; CI artifact assertion requires non-secret environment manifests; empty-result and compare `NO_MATCH` false-pass guards covered; release gates pass for package inspection, fresh install, public artifact classification, release-blocker disposition structure, and Leonardo evidence helper contracts | Branch protection/release-policy enforcement still separate |
| Gate 10 — Security/release hygiene | Partial pass, improved | `SECURITY.md`, hygiene doc, compliance boundary doc, compatibility matrix, release checklist, external evidence request doc, artifact classifier, token regression test, package inspector, rebuilt wheel/sdist proof, audit-tooling package exclusion, CI package-content/fresh-install/classification gates | Third-party/formal compliance review and remote non-Windows CI execution evidence still missing |

## Current label

**PRODUCT READY for audited developer/software scope.**

## 2026-05-18 external evidence unblock update

- Added local validators/request tooling for remaining external blockers:
	- `scripts/assert_remote_ci_matrix_evidence.py`
	- `scripts/run_serious_workflow_provider_evidence.py`
	- `scripts/write_ci_environment.py`
	- `docs/mbs_enterprise_external_evidence_requests.md`
- CI now emits `benchmarks/results/ci_environment.json`; both local and remote CI artifact checks require it.
- Generated request artifacts showing honest status: `benchmarks/results/remote_ci_matrix_evidence_REQUESTED.json` is `FAIL` because downloaded remote artifacts are absent, and `benchmarks/results/serious_workflow_provider_plan/manifest.json` is `NO_EVIDENCE_DRY_RUN` until reviewed provider responses are supplied.
- Full local repository validation: `212 passed, 10 skipped`.
- Readiness label unchanged because remote CI artifacts, provider-classified serious workflow responses, broader passing OSS/HPC/closed-provider evidence, and third-party compliance/security review remain external blockers.

## Latest implementation progress

2026-05-16:
- Started execution of the enterprise plan with Priority 0 product bug hardening.
- Added controlled CLI input errors for invalid JSON files.
- Expanded BOM-safe reading for benchmark JSONL, report result JSON, and gate config files.
- Added Windows BOM/CRLF regression tests for `validate`, `cost`, `report`, and `gate`.
- Targeted tests passed: `2 passed, 75 deselected`.
- Full product test file passed: `77 passed`.

2026-05-16 slice 2:
- Expanded BOM-safe artifact reading to `triage` and `retry-audit`.
- Added BOM regression coverage for `adapt-responses`, `compare`, `triage`, `retry-audit`, and `evidence-pack`.
- Targeted artifact-reader tests passed: `3 passed, 75 deselected`.
- Full product test file passed: `78 passed`.

2026-05-16 slice 3:
- Converted additional routine CLI mistakes to controlled `MBS input error` responses.
- Hardened `cost`, `bench`, config loading, records loading, and `agent-tools` misuse behavior.
- Added record-array object validation to prevent downstream AttributeError on malformed records.
- Targeted controlled-error tests passed: `2 passed, 77 deselected`.
- Full product test file passed: `79 passed`.
- Full repository test suite passed: `151 passed, 10 skipped`.

2026-05-16 slice 4:
- Tightened empty result handling so empty summary/rows payloads are not counted as evidence rows.
- Added explicit `report`/`gate` empty-result failure tests.
- Added compare `NO_MATCH` reason and CLI/API non-pass regression tests.
- Patched high-use provider/evidence/tuning script readers to accept UTF-8 BOM artifacts.
- Targeted tests passed: `3 passed, 79 deselected`.
- Full product test file passed: `82 passed`.
- Full repository test suite passed: `154 passed, 10 skipped`.

2026-05-16 slice 5:
- Added validation `failure_reason` for machine-readable failure handling.
- Added top-level `check --json` contract fields: `status`, `failure_reason`, `trace_id`, `schema_hash`, and `contract_hash`.
- Hardened nested trace output paths for `check --trace-out` and `trace --out`.
- Focused tests passed: `4 passed, 80 deselected`.
- Full product test file passed: `84 passed`.
- Full repository test suite passed: `156 passed, 10 skipped`.

2026-05-16 slice 6:
- Added `failure_reason` to trace records and gate results.
- Extended invalid `check` contract coverage so validation failures propagate into traces.
- Added inline misuse coverage for non-object `agent-tools --args`.
- Focused tests passed: `4 passed, 80 deselected`.
- Full product test file passed: `84 passed`.
- Full repository test suite passed: `156 passed, 10 skipped`.

2026-05-17 slice 7:
- Added `examples/incident_response_runbook/` as a serious structured-output workflow fixture, not just a toy schema.
- Added strict nested schema, eight incident cases, operational policy, passing/failing response fixtures, and workflow-specific gate thresholds.
- Added product regression coverage that adapts responses, checks schema and semantic rates, gates the good fixture, builds an evidence pack, and confirms the bad fixture fails with expected taxonomy.
- Focused incident workflow test passed: `1 passed, 84 deselected`.
- Full product test file passed: `85 passed`.
- Full repository test suite passed: `157 passed, 10 skipped`.

2026-05-17 slice 8:
- Upgraded `examples/fintech_transaction_risk/` from a toy example into a serious transaction-risk workflow fixture.
- Added strict nested schema, eight transaction cases, operational policy, passing/failing response fixtures, and workflow-specific gate thresholds.
- Added product regression coverage that adapts responses, checks schema and semantic rates, gates the good fixture, builds an evidence pack, confirms copied raw results, and confirms the bad fixture fails with expected taxonomy.
- Updated BOM conformance coverage against the stricter fintech schema.
- Focused fintech workflow test passed: `1 passed, 85 deselected`.
- Full product test file passed: `86 passed`.
- Full repository test suite passed: `158 passed, 10 skipped`.

2026-05-17 slice 9:
- Upgraded `examples/support_ticket_triage/` from toy validation into a third serious workflow fixture.
- Added strict nested schema, eight support-ticket cases, operational routing/safety policy, passing/failing response fixtures, and workflow-specific gate thresholds.
- Added product regression coverage that adapts responses, checks schema and semantic rates, gates the good fixture, builds an evidence pack, confirms copied raw results, and confirms the bad fixture fails with expected taxonomy.
- Focused support workflow test passed: `1 passed, 86 deselected`.
- Full product test file passed: `87 passed`.
- This satisfies the three serious workflow-pack software fixture requirement, but it is still not provider-classified evidence and does not justify enterprise pilot/production readiness.

2026-05-17 slice 10:
- Verified clean release repo/venv and import paths from `D:\projects\mbs-public-release`.
- Re-verified BOM JSON behavior and added agent-tool `output_path` BOM coverage.
- Hardened routine CLI file/schema mistakes to controlled errors without tracebacks.
- Added `output_path` support for JSON-callable agent tools and aligned Python `check()` result with top-level failure/trace/hash fields.
- Added external-user smoke test and replayable transaction-review agent workflow proof.
- Re-verified the three serious workflow fixture packs: good gates pass and bad gates fail.
- Focused agent/contract tests passed: `4 passed`.
- Full repository test suite passed: `162 passed, 10 skipped`.
- Status remains below Enterprise Pilot Ready because provider-classified evidence, release/security hygiene, CI matrix, and cross-platform proof are still open.

2026-05-17 P0 executor batch verification:
- Confirmed active repo and import paths from `D:\projects\mbs-public-release` using the external audit venv.
- Re-verified Windows BOM output/schema/request JSON handling, controlled CLI errors, regression coverage, external-user smoke flow, transaction-review workflow, machine-readable JSON output, hard workflow fixtures, adversarial cases, and CI/regression gate assertions.
- Focused P0 tests passed locally: `130 passed`.
- External-user smoke test passed and wrote `external_user_smoke_test\command_transcript.txt`.
- Transaction-review agent workflow passed and wrote replay artifacts under `examples\agent_workflow_transaction_review\artifacts`.
- Full local repository validation passed: `193 passed, 10 skipped`.
- Current label remains **PRODUCT READY for audited developer/software scope**. Do not upgrade to Enterprise Pilot Ready until provider-classified evidence, remote CI matrix evidence, broader provider/OSS proof, and formal security/compliance review are complete.

2026-05-17 provider/model evidence execution update:
- Added LM Studio runner dry-run support and regression coverage; focused nested provider test passed: `5 passed`.
- Generated no-secret dry-run artifacts for LM Studio, Ollama tiny/small, vLLM/OpenAI-compatible, and HPC collection paths.
- Captured a real scoped Azure Sweden `gpt-5.5` nested tool-call run from 25 cases: 25 traceable rows, 0 infrastructure failures, schema-valid rate `1.0000`, semantic-correct rate `0.8800`, clean-JSON rate `1.0000`, provider gate `PASS`.
- Classified the Azure response artifact as provider evidence requiring review before sharing; no blocking secret findings were reported.
- Recorded blockers for inactive local OSS endpoints, missing five-family OSS responses, remote HPC/live large-model evidence, absent Anthropic/Gemini/Cohere credentials, and missing provider-classified serious-workflow runs.
- Current label remains **PRODUCT READY for audited developer/software scope**. The new Azure run improves Gate 6/7 evidence but does not close Enterprise Pilot Ready blockers.

2026-05-17 Leonardo HPC evidence execution update:
- Added Leonardo-specific HF-local runner, SLURM submitter, and environment checker under `scripts/`.
- Resolved operational blockers for safe Leonardo execution: QOS wall-time, compute-node no-internet, existing Python environment selection, full home/work filesystems, scratch HF cache/output, and offline/local-files compute mode.
- Collected live `hpc` nested structured-output evidence on Leonardo and mirrored artifacts under `benchmarks/results/leonardo_mbs_hpc_20260517/`.
- Live behavior evidence now exists for TinyLlama, Qwen 0.5B/1.5B/3B/7B, and Mistral 7B; all currently fail nested gate thresholds due to semantic/schema/clean-JSON failures. Phi 3.5 mini is infra/local-load failure only.
- This improves Gate 7 breadth but does not upgrade readiness: the current label remains **PRODUCT READY for audited developer/software scope**.

2026-05-16 release hygiene slice:
- Added `SECURITY.md` for vulnerability reporting, credential handling, artifact sensitivity, and current readiness boundaries.
- Added `docs/mbs_security_privacy_release_hygiene.md` with current guarantees, operator responsibilities, release exclusions, credential-scan baseline, and Gate 10 boundaries.
- Added `SECURITY.md` to `MANIFEST.in` and linked the hygiene doc from `README.md`.
- Added release-hygiene regression tests for docs, `.gitignore`, and high-confidence token scanning.
- Focused release-hygiene tests passed: `3 passed`.
- Gate 10 improves from unknown to partial, but still does not satisfy Enterprise Pilot Ready without artifact classification, package-content proof, formal compliance boundary, and CI/cross-platform execution.

2026-05-16 release package proof slice:
- Added `scripts/assert_release_package.py` for wheel/sdist content inspection.
- Added package regression tests covering manifest inclusion, clean packages, and forbidden local artifacts.
- Excluded `mbs_product_readiness_audit*` from package discovery and pruned `mbs_product_readiness_audit` from source distributions.
- Rebuilt `dist/mbs-0.1.1.tar.gz` and `dist/mbs-0.1.1-py3-none-any.whl`.
- Package inspector passed on rebuilt artifacts: wheel `28` files, sdist `187` files, no forbidden local artifacts.
- Added CI steps to build release packages and run the package inspector before evidence generation.
- Local validations: full pytest `168 passed, 10 skipped`; focused release checks `6 passed`; package inspector `PASS`.
- Added `scripts/assert_fresh_install.py` and CI wiring to prove the built wheel installs and runs from a temporary clean virtual environment.
- Focused release/install checks passed: `8 passed`; package inspector `PASS`; fresh install proof `PASS`.
- Gate 10 is stronger but still partial until non-Windows package proof, formal compliance boundaries, and artifact classification are complete.

2026-05-16 artifact/compliance/cross-platform slice:
- Added `scripts/classify_release_artifacts.py` to classify artifacts by evidence class, sensitivity, sharing boundary, and review requirement.
- Added `tests/test_artifact_classification.py` covering public sample artifacts, provider-review artifacts, and blocking secret findings.
- Added `docs/mbs_compliance_security_boundary.md` as the formal local compliance/security boundary for MBS v0.1.1.
- Updated release hygiene docs and README to reference artifact classification and the compliance boundary.
- Expanded `.github/workflows/mbs-ci.yml` to a three-OS matrix: Ubuntu, Windows, and macOS.
- Added artifact classification as a CI release gate for public CI artifacts.
- Validation passed locally: full pytest `173 passed, 10 skipped`; package check `PASS`; fresh install check `PASS`; artifact classification `PASS`.
- Remaining Gate 10 boundary: remote CI matrix execution and any third-party/formal compliance review are still outside this local implementation.

2026-05-16 CI workflow assertion and release checklist slice:
- Added `tests/test_ci_release_workflow.py` to regression-guard the three-OS CI matrix, Python 3.11 runtime, package build, package inspection, fresh install proof, artifact classification, CI artifact assertion, and matrix-scoped artifact uploads.
- Added `docs/mbs_enterprise_compatibility_matrix.md` documenting runtime/OS support targets, configured non-Windows proof, release hygiene gates, shell considerations, and current limitations.
- Added `docs/mbs_release_readiness_checklist.md` with the required pre-release command sequence, artifact classification rules, and safe/not-safe release decision language.
- Wired the new docs/test into `README.md`, `MANIFEST.in`, `scripts/assert_release_package.py`, and release package fixture tests.
- Validation passed locally: full pytest `176 passed, 10 skipped`; package check `PASS`; fresh install check `PASS`; artifact classification `PASS`.
- Remaining boundary: this proves local configuration and packaging discipline, not remote GitHub Actions execution or third-party compliance review.

2026-05-16 blocker disposition and public CLI matrix slice:
- Added `docs/mbs_enterprise_blocker_disposition.md` to assign remaining readiness blockers to owners, severities, target labels, planned evidence artifacts, verification commands, status, dates, and closure conditions.
- Added a broad public CLI success-path command matrix regression covering `compile`, `validate`, `check`, `trace`, `cost`, `bench`, `demo`, `test`, `lang`, `report`, `gate`, `evidence-pack`, `compare`, `retry-audit`, `models`, `triage`, `agent-tools`, `adapt-responses`, and `make-response-template`.
- Fixed the matrix fixture so `triage` receives the required `valid_json_rate` summary field.
- Wired the blocker-disposition doc into `README.md` and release package inspection requirements.
- Validation passed locally: focused CLI matrix test `1 passed`; full pytest `177 passed, 10 skipped`; package check `PASS`; fresh install check `PASS`; artifact classification `PASS`.
- Remaining boundary: this closes the local success-path command-surface gap, but not the broader negative/edge command matrix, remote CI evidence, provider-classified evidence, or formal compliance review.

2026-05-16 JSON robustness matrix slice:
- Added conformance regressions for malformed inline JSON through the public `validate --json` CLI path, malformed fenced JSON, non-object JSON against object schemas, and deterministic first-object extraction when prose contains multiple JSON objects.
- Confirmed these cases fail cleanly with machine-readable `invalid_json` or `wrong_type` reasons and no Python traceback.
- Focused conformance validation passed locally: `29 passed`.
- Full local repository validation passed: `181 passed, 10 skipped`.
- Remaining boundary: this extends local validator/CLI robustness but does not yet prove all standalone scripts, provider raw-output formats, or remote non-Windows executions.

2026-05-16 release-gate classifier refinement:
- Refined artifact classification so expected public release docs (`README.md`, `SECURITY.md`, `LICENSE`, `MANIFEST.in`, `pyproject.toml`) are classified as docs.
- Suppressed public security-contact email findings for `SECURITY.md` while retaining secret/token blocking and sensitive raw-artifact review behavior.
- Rebuilt release artifacts and validated package/fresh-install/classification gates.
- Validation passed locally: full pytest `182 passed, 10 skipped`; package check `PASS`; fresh install `PASS`; artifact classification `PASS` for 7 public release artifacts with `0` review-required and `0` blocking findings.
- Remaining boundary: local packaging/release hygiene is stronger, but remote CI execution and formal external compliance/security review remain open.

## Not allowed labels

- ENTERPRISE PILOT READY: **not allowed yet**.
- ENTERPRISE PRODUCTION READY: **not allowed yet**.
- Fully ready for all models/providers/schemas/safety scenarios: **not allowed**.

## 2026-05-18 direct GitHub/Azure evidence update

- GitHub Actions run `26011084310` completed successfully and downloaded artifacts validate as `legacy_remote_ubuntu_ci_execution` in `benchmarks/results/legacy_remote_ci_evidence_26011084310.json`.
- The GitHub run does not close the three-OS matrix blocker because remote `main` still used the old single-artifact workflow; the updated matrix workflow must be pushed/rerun before claiming Windows/macOS evidence.
- Azure Sweden `gpt-5.5-2` serious-workflow provider evidence passes all three serious workflows after clarifying the fintech moderate-risk policy ambiguity:
	- incident-response/runbook: `PASS`, 8 runs;
	- fintech transaction-risk: `PASS`, 8 runs;
	- support-ticket triage: `PASS`, 8 runs.
- Evidence manifest: `benchmarks/results/serious_workflow_provider_evidence_azure_pass_candidate/manifest.json`.
- Full local repository validation after the evidence/tooling updates: `213 passed, 10 skipped`; focused external/product/release validation: `102 passed`.
- Gate 8 is now pass for Azure provider pilot evidence, but broader cross-provider replications remain pending.
- Readiness label remains **PRODUCT READY for audited developer/software scope** until remote three-OS CI matrix evidence, broader passing provider/OSS/HPC matrix evidence, and formal compliance/security review are complete.

## 2026-05-18 remote matrix CI fix update

- The first updated GitHub three-OS matrix run (`26011511225`) reached Ubuntu, Windows, and macOS runners but failed at `mbs gate` because the deterministic CI mock was not strict-schema aware.
- Fixed the deterministic CI benchmark path in commit `e2242f5` by adding schema-aware mock handling for `const`, transaction ID patterns, required arrays, bounded numeric values, and fintech risk/decision semantics.
- Added regression coverage for the strict fintech CI benchmark and revalidated locally: focused CI/external tests `11 passed`, CI artifact assertion `PASS`, full suite `214 passed, 10 skipped`.
- Replacement GitHub Actions matrix run `26011688420` completed `success` on Ubuntu, Windows, and macOS. Downloaded artifacts validate as `PASS` in `benchmarks/results/remote_ci_matrix_evidence_26011688420.json`.
- Patched `scripts/assert_remote_ci_matrix_evidence.py` to support GitHub's preserved `benchmarks/results/` artifact layout and added regression coverage; latest full local suite is `215 passed, 10 skipped`.
- Gate 1 remote three-OS execution evidence and Gate 9 remote CI matrix evidence are now closed for the current branch evidence package.
- Current readiness label remains **PRODUCT READY for audited developer/software scope** because broader passing provider/OSS/HPC matrix evidence and formal compliance/security review are still open.

## Required score for ENTERPRISE PILOT READY

- Gates 1-6: pass.
- Gate 7: at least pilot matrix pass.
- Gate 8: at least three serious workflow packs pass. **STATUS: COMPLETE for software fixtures; provider-classified runs still required for readiness claims.**
- Gate 9: pass for CI gate/regression behavior.
- Gate 10: pass for release hygiene.

## Required score for ENTERPRISE PRODUCTION READY

- Gates 1-10: pass.
- Broad model/provider/schema matrix complete.
- Cost/latency/retry/failure maps complete.
- Trace persistence/export durability proven.
- Operational docs and support model complete.