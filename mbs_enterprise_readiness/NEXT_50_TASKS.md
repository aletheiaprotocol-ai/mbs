# Next 50 Tasks

## Product bug hardening first

1. Re-test UTF-8 BOM input across every CLI JSON reader. **P0 RE-VERIFIED 2026-05-17 — validate/cost/report/gate/adapt-responses/compare/triage/retry-audit/evidence-pack covered; high-use provider/evidence/tuning scripts patched. Remaining: deeper standalone script matrix.**
2. Re-test UTF-8 BOM handling for generated artifacts consumed by MBS tools. **P0 RE-VERIFIED 2026-05-17 — report/gate/evidence-pack/compare/triage/retry-audit and high-use script readers covered/patched. Remaining: less-common artifact readers/provider raw outputs.**
3. Add Windows CRLF + BOM JSON fixture tests. **P0 RE-VERIFIED — core CLI and artifact commands covered by focused P0 tests.**
4. Add invalid inline JSON controlled-error tests. **P0 RE-VERIFIED/PARTIAL — malformed inline validate path, agent-tools request path, and non-object args covered; more command-specific inline cases remain.**
5. Add invalid file JSON controlled-error tests. **P0 RE-VERIFIED/PARTIAL — validate schema/output, bench config, and cost records covered without tracebacks.**
6. Add no-traceback tests for routine CLI mistakes. **P0 RE-VERIFIED/PARTIAL — missing schema/output paths, invalid schemas, missing cost inputs, bench config misuse, config/records shape errors, and agent-tool misuse covered.**
7. Add schema path/output path consistency tests. **PARTIAL COMPLETE — `check --trace-out` and `trace --out` nested output paths covered.**
8. Add empty benchmark result fail tests. **COMPLETE for report/gate empty result behavior.**
9. Add `NO_MATCH` false-pass prevention tests. **COMPLETE for compare Python API and CLI.**
10. Add CLI JSON output contract tests for status/failure reason/trace ID. **PARTIAL COMPLETE, IMPROVED — `validate`, `check --json`, Python `check()`, agent-tool `mbs.check`, trace records, and gate results covered.**

## CLI/API/agent surface

11. Complete command matrix tests for `compile`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
12. Complete command matrix tests for `validate`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
13. Complete command matrix tests for `check`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
14. Complete command matrix tests for `trace`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
15. Complete command matrix tests for `bench`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
16. Complete command matrix tests for `test`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
17. Complete command matrix tests for `agent-tools`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
18. Complete command matrix tests for `demo`. **SUCCESS PATH COMPLETE — covered in public CLI matrix regression; negative edge cases remain.**
19. Add retry recommendation field where applicable.
20. Add schema/contract hash field where applicable. **PARTIAL COMPLETE — `check --json` exposes `schema_hash` and `contract_hash`.**

## Hard schemas

21. Create incident response/runbook schema pack. **COMPLETE as software fixture — strict nested schema, eight cases, good/bad response fixtures, workflow gate, and evidence-pack regression added. Remaining: real provider-classified runs.**
22. Create fintech transaction risk schema pack. **COMPLETE as software fixture — strict nested schema, eight cases, good/bad response fixtures, workflow gate, evidence-pack regression, and BOM conformance update added. Remaining: real provider-classified runs.**
23. Create support escalation schema pack. **COMPLETE as software fixture — strict nested support triage schema, eight cases, good/bad response fixtures, workflow gate, evidence-pack regression, and failure taxonomy checks added. Remaining: real provider-classified runs.**
24. Create source-grounded claim review schema pack.
25. Create medical-legal/QME review schema pack.
26. Create cybersecurity incident triage schema pack.
27. Create agent tool-call safety schema pack.
28. Create memory-write admission schema pack.
29. Create multilingual structured-output schema pack.
30. Create audit packet generation schema pack.

## Benchmark engine and metrics

31. Add row-level failure taxonomy export.
32. Add retry/no-retry comparison output.
33. Add failure-specific retry comparison output.
34. Add semantic retry comparison output.
35. Add cost per valid output metric.
36. Add cost per semantically correct output metric.
37. Add latency summary and percentiles.
38. Add model/provider/version manifest validation.
39. Add schema/case/prompt version manifest validation.
40. Add artifact completeness assertion for serious runs.

## May 17, 2026 Leonardo 70B quantization update

- Installed `bitsandbytes==0.49.2` into `/leonardo_work/AIFAC_F02_151/mbs_env`.
- Verified CUDA/A100 import in Leonardo GPU job `41800732`.
- Retrieved and classified cached/local-files-only 70B 4-bit retry job `41800766` with `JOB_LABEL=large_70b_4bit_bnb`: 8 behavior rows, 0 infra failures, schema-valid `1.0`, semantic-correct `0.5`, clean-JSON `0.0`, gate `FAIL`.
- Added and ran `scripts/crosscheck_leonardo_hpc_artifacts.py` to replay mirrored HPC raw responses through standard MBS adapter/report/gate APIs: 21 model artifacts, 295 total runs, 0 missing trace rows, aggregate gate `FAIL`.
- Added `tests/test_leonardo_hpc_crosscheck.py` regression coverage for the Leonardo runner contract, compact prompt, clean-vs-embedded JSON parsing, gate clean-JSON requirement, UTF-8-SIG manifest reading, and cross-check records; focused validation now `18 passed`.
- Retrieved and classified compact prompt comparison job `41807858`: Qwen-14B and Yi-9B are behavior evidence but fail gates; 70B compact row is infra-only in the multi-model run due GPU/offload load failure. Standard MBS replay now covers 24 files and 331 traceable runs with aggregate gate `FAIL`.
- Added `scripts/summarize_leonardo_hpc_artifacts.py`; patched Leonardo runner for incremental response writes, row progress logs, matrix prompt-style metadata, and CUDA cleanup between sequential models.
- Expanded focused Leonardo/HPC regression validation to `20 passed`.
- Added `tests/test_leonardo_shell_wrappers.py` to guard offline SLURM submitter settings and the single-model 70B compact retry wrapper; focused validation now `22 passed`.
- Submitted and retrieved compact 70B single-model/fresh-process retry `41807878` via `scripts/submit_leonardo_70b_compact_single.sh`: job completed, 8 behavior rows, 0 infra failures, schema-valid `0.75`, semantic-correct `0.375`, clean-JSON `0.0`, gate `FAIL`.
- Full local repository validation after Leonardo/HPC additions and YAML test portability fix: `204 passed, 10 skipped`.
- Added Leonardo regression tests to source-package manifest coverage and release package fixtures; focused package validation passed (`13 passed`).
- Added Leonardo summarizer regression coverage for multi-model compact run manifests while excluding derived `standard_mbs` manifests; focused validation passed (`9 passed`).
- Full local repository validation after package/summarizer hardening: `205 passed, 10 skipped`.
- Added release-blocker disposition regression coverage requiring required fields and all ten Enterprise Pilot gates to retain unresolved-boundary language; full local repository validation now passes: `206 passed, 10 skipped`.
- Refreshed Leonardo local mirror summary to 25 result rows and standard MBS replay to 339 traceable case rows, 0 missing trace rows, aggregate gate `FAIL`.
- Added `--out` support to the Leonardo standard MBS cross-check script so summary paths are explicit and scriptable; regression validation passed (`10 passed`).
- Full local repository validation after the explicit cross-check summary output support: `207 passed, 10 skipped`.
- Added external-evidence unblock tooling: `scripts/assert_remote_ci_matrix_evidence.py`, `scripts/run_serious_workflow_provider_evidence.py`, `scripts/write_ci_environment.py`, and `docs/mbs_enterprise_external_evidence_requests.md`.
- CI now records non-secret `ci_environment.json` per run; local and remote CI artifact validators require it.
- Generated local request artifacts: `benchmarks/results/remote_ci_matrix_evidence_REQUESTED.json` shows remote CI artifacts still missing, and `benchmarks/results/serious_workflow_provider_plan/manifest.json` lists exact serious-workflow provider response files needed.
- Full local repository validation after external-evidence unblock tooling: `212 passed, 10 skipped`.
- Remaining action: obtain remote CI artifacts, reviewed provider serious-workflow JSONL, broader passing OSS/HPC/closed-provider evidence, and formal compliance/security review; current evidence still does not allow Enterprise Pilot Ready.

## May 16, 2026 release hygiene and compatibility update

- Package-content proof, fresh wheel install proof, artifact classification, compliance/security boundary, cross-platform CI configuration, CI workflow assertion tests, compatibility matrix, release checklist, and blocker disposition are complete locally.
- Latest full local validation: `176 passed, 10 skipped`; package check `PASS`; fresh install proof `PASS`; artifact classification `PASS`.
- Cross-platform CI is configured and regression-guarded for Ubuntu, Windows, and macOS, but remote GitHub Actions run evidence is still not captured.
- Remaining blockers are formally tracked in `docs/mbs_enterprise_blocker_disposition.md`.
- Still not Enterprise Pilot Ready: remote CI run evidence, provider-classified serious workflow runs, broader provider/OSS matrix, full command/JSON robustness matrix, and formal compliance/security review remain open.

## May 17, 2026 P0 execution update

- Clean audit venv verification completed against `D:\projects\mbs-public-release`.
- BOM output JSON bug re-verified; added agent-tool `output_path` BOM regression coverage.
- External-user smoke test added and passing.
- Transaction-review agent workflow proof added and passing.
- Three serious workflow software fixture packs explicitly re-verified: good gates pass, bad gates fail.
- Full repository suite: `162 passed, 10 skipped`.
- Still not Enterprise Pilot Ready: provider-classified runs, remote CI run evidence, formal compliance review, and broader provider/OSS proof remain open.

## May 17, 2026 P0 executor batch verification

- Completed the 15-item safe local P0 verification batch in the external audit venv.
- Confirmed repo/import path: `D:\projects\mbs-public-release`, `mbs\__init__.py`, `mbs\cli.py`, version `0.1.1`.
- Re-verified Windows BOM JSON handling, BOM/schema/output regressions, controlled CLI errors, focused tests, full tests, external smoke flow, transaction-review workflow, machine-readable JSON output, hard workflow fixtures, adversarial fixture cases, and CI/regression gate assertions.
- Focused P0 regression pack passed: `130 passed`.
- Full repository suite passed: `193 passed, 10 skipped`.
- Current readiness label remains **PRODUCT READY for audited developer/software scope**, not Enterprise Pilot Ready.
- Next unblocked safe local task: task 43, build the LM Studio runner plan, unless negative/edge CLI matrix expansion is prioritized first.

## May 17, 2026 provider evidence scaffolding update

- Added and regression-tested `scripts/run_nested_provider_evidence.py` for B-007/B-008 scaffolding.
- Runner supports no-secret dry-run plans, response-template generation, existing response JSONL reuse, `fixture`/`provider`/`oss`/`hpc` classification, artifact classification, gate/evidence-pack generation, and secret-bearing response blocking.
- Compatibility artifacts are emitted for both new and legacy tests: `manifest.json`, `run_plan.json`, `run_manifest.json`, copied gate/triage JSON, README, and `evidence_pack/`.
- Full repository suite after compatibility fixes: `192 passed, 10 skipped`.
- Boundary remains unchanged: the runner is scaffolding and response-file evidence plumbing; real provider/OSS/HPC runs are still open until collected from reviewed non-secret response JSONL or endpoints.

## Provider/model/compute evidence

41. Build vLLM OpenAI-compatible runner plan. **PARTIAL COMPLETE — nested provider evidence runner now writes dry-run commands/templates for OpenAI-compatible collection; actual endpoint run still pending.**
42. Build Ollama runner plan. **PARTIAL COMPLETE — nested provider evidence runner now writes no-secret Ollama dry-run commands/templates with default `http://localhost:11434`; actual Ollama response collection still pending.**
43. Build LM Studio runner plan. **COMPLETE LOCALLY — `--runner lm-studio` now emits no-secret OpenAI-compatible collection plans against `http://localhost:1234` with `LM_STUDIO_API_KEY`; regression test added and passing. Real LM Studio evidence remains pending until a local server/model is running.**
44. Run OSS smoke matrix on tiny/small models. **PARTIAL LIVE COMPLETE VIA LEONARDO — added self-contained HF-local runner and collected live `hpc` smoke evidence under `benchmarks/results/leonardo_mbs_hpc_20260517/smoke_41796661/`. Behavior evidence exists for TinyLlama, Qwen 0.5B/1.5B/3B, and Mistral 7B; all failed gate thresholds, mostly semantic/schema/clean-JSON issues. Phi 3.5 mini produced infra/local-load failures and is excluded from behavior claims.**
45. Run medium OSS matrix across at least five families. **IN_PROGRESS/PARTIAL VIA LEONARDO — medium models were mostly cached to scratch before the login-node download was killed; targeted jobs produced Qwen2.5-7B/14B, DeepSeek-R1-Distill-Qwen-7B, Yi-1.5-6B, Granite-8B, Mistral-Nemo, and Phi-4 evidence under `benchmarks/results/leonardo_mbs_hpc_20260517/`, all gate FAIL so far. Additional cached-family runs remain pending.**
46. Run selected large/HPC matrix. **IN_PROGRESS VIA LEONARDO — remote submission blocker is resolved for safe local/offline GPU jobs; scripts now support scratch cache/output, `JOB_LABEL`, `PROMPT_STYLE`, and local-files-only compute execution. `bitsandbytes==0.49.2` is installed/GPU-verified, 70B 4-bit behavior job `41800766` completed but failed gate thresholds, compact multi-model job `41807858` produced Qwen/Yi behavior evidence plus infra-only 70B load failure, and single-model 70B compact retry `41807878` completed as behavior evidence but failed gate thresholds. Standard MBS replay now covers 25 result files and 339 traceable case rows.**
47. Run Azure/OpenAI closed-provider matrix. **PARTIAL COMPLETE — Sweden Azure `gpt-5.5` tool-call nested run completed locally: 25 runs, 0 infra failures, schema-valid 1.0000, semantic-correct 0.8800, clean JSON 1.0000, gate PASS. The earlier wrong-endpoint `DeploymentNotFound` artifact remains classified as infrastructure failure, not behavior evidence. Broader OpenAI/closed-provider matrix remains pending.**
48. Run Anthropic/Gemini/Cohere matrix if credentials are available. **BLOCKED — env presence artifact shows `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY`, and `COHERE_API_KEY` absent. Request needed: set those provider keys or provide reviewed response JSONL. External evidence request doc now captures the required non-secret response-artifact path.**
49. Produce model-family failure maps. **PARTIAL COMPLETE, UPDATED WITH LEONARDO — added current Azure map plus live Leonardo HF-local smoke/medium failure clusters. Broader OSS/HPC and closed-provider coverage remains incomplete.**
50. Update scorecard and readiness label from evidence only. **DONE FOR THIS BATCH, RECONFIRMED AFTER EXTERNAL-EVIDENCE TOOLING — scorecard/blockers updated from actual evidence. Readiness label unchanged: PRODUCT READY for audited developer/software scope; not Enterprise Pilot Ready.**

## May 18, 2026 direct GitHub/Azure evidence update

- Real Azure Sweden `gpt-5.5-2` serious-workflow provider evidence now passes all three serious workflows after clarifying the fintech moderate-risk policy ambiguity for known-device/new-payee/no-geo transactions.
- Evidence: `benchmarks/results/serious_workflow_provider_evidence_azure_pass_candidate/manifest.json` with incident-response/runbook, fintech transaction-risk, and support-ticket triage all `PASS` across 24 provider rows.
- GitHub Actions run `26011084310` completed `success`; downloaded artifacts validate as `legacy_remote_ubuntu_ci_execution` in `benchmarks/results/legacy_remote_ci_evidence_26011084310.json`.
- Boundary: the successful GitHub run used the old remote `main` workflow and is Ubuntu-only legacy proof. It does not close the three-OS matrix blocker until the updated matrix workflow is pushed/rerun and `scripts/assert_remote_ci_matrix_evidence.py` passes on Ubuntu/Windows/macOS artifacts.
- Validation after updates: focused external/product/release tests `102 passed`; full repository suite `213 passed, 10 skipped`.
- Readiness label remains **PRODUCT READY for audited developer/software scope** until remote three-OS CI matrix evidence, broader passing provider/OSS/HPC matrix evidence, and formal compliance/security review are complete.