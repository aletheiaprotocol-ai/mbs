# Release Blockers

## Blocks broad ready claim now

- Current evidence is too narrow.
- Serious workflow software fixtures now exist, but provider-classified evidence is still missing.
- Broad model/provider matrix is missing.
- Security/release hygiene audit is substantially improved: package-content proof, fresh-install proof, artifact classification, compliance boundary docs, compatibility matrix, release checklist, cross-platform CI configuration/regression guard, remote-CI artifact validator, and external evidence request doc now exist. Remote CI execution artifacts and formal/third-party compliance review are still missing.
- Enterprise docs are improved with compatibility and release-readiness artifacts, but external enterprise/security/procurement review remains missing.

## Blocks ENTERPRISE PILOT READY

1. Gate 1 cross-platform execution is configured and regression-guarded in CI, CI now writes non-secret environment manifests, and local Windows audit venv import/tests passed again on 2026-05-18, but remote non-Windows run artifacts are not yet captured. Exact request: download `mbs-ci-artifacts-ubuntu-latest-py3.11`, `mbs-ci-artifacts-windows-latest-py3.11`, and `mbs-ci-artifacts-macos-latest-py3.11`, then run `python scripts/assert_remote_ci_matrix_evidence.py --artifacts-dir benchmarks/results/remote_ci_artifacts --out benchmarks/results/remote_ci_matrix_evidence.json`.
2. Gate 2 public CLI success-path matrix and P0 JSON/controlled-error regressions are covered locally, but broader negative/edge command matrix and remote cross-platform execution evidence are still incomplete.
3. Gate 3 JSON robustness is improved and P0 re-verified for BOM, controlled file/input failures, prose-wrapped JSON, fenced JSON, malformed inline/fenced JSON, non-object JSON, deterministic multi-object prose extraction, strict bool/type handling, and safety-review warnings, but standalone script and broader provider/raw-output malformed JSON matrix coverage is still incomplete.
4. Gate 4 hard-schema validation is strong for current local software fixtures, including incident-response, fintech, support, transaction-review, and adversarial packs, but real provider adversarial evidence remains missing.
5. Gate 5 agent output contract is locally proven for key paths, including `output_path`, smoke flow, transaction workflow, and machine-readable JSON output, but not yet enterprise-complete across all integrations.
6. Gate 6 benchmark breadth remains incomplete beyond local fixtures and scoped provider scaffolding.
7. Gate 7 provider/OSS coverage remains too narrow but is improving. Azure Sweden `gpt-5.5` nested tool-call evidence exists for one scoped 25-case run, and live Leonardo HF-local `hpc` evidence now exists for TinyLlama, Qwen 0.5B/1.5B/3B/7B/14B, Mistral 7B/Nemo, DeepSeek-Qwen 7B/14B, Yi, Granite, Phi, OLMo, Gemma, SmolLM, and 70B Llama families. Current Leonardo runs failed nested gate thresholds; 70B 4-bit job `41800766` completed as behavior evidence but failed due semantic/non-clean JSON issues. Compact Qwen/Yi prompt comparison from job `41807858` also failed gates, and its 70B multi-model row was infrastructure-only; single-model 70B compact retry `41807878` completed as behavior evidence but failed due schema/semantic/non-clean JSON issues. Standard MBS replay currently covers 25 mirrored result files and 339 traceable runs, aggregate gate `FAIL`. Broader OSS/HPC/closed-provider matrices remain incomplete.
8. Gate 8 real workflow packs are complete as software fixtures and re-verified locally, one scoped Azure nested-tool provider run exists, and `scripts/run_serious_workflow_provider_evidence.py` now creates exact collection/build plans, but real provider-classified runs for the serious workflow packs are still missing. Exact request: provide reviewed non-secret `incident_response_runbook.jsonl`, `fintech_transaction_risk.jsonl`, and `support_ticket_triage.jsonl`, then run the verification command in `docs/mbs_enterprise_external_evidence_requests.md`.
9. Gate 9 regression guards improved locally and CI matrix is configured/tested; latest local full suite is `212 passed, 10 skipped`, but remote CI matrix run evidence remains incomplete.
10. Gate 10 security/release hygiene partial only: `SECURITY.md`, hygiene doc, compliance boundary, compatibility matrix, release checklist, artifact classifier, token-regression test, package proof, fresh-install proof, CI package/classification gates, and exact external evidence request doc exist; formal third-party compliance review and remote non-Windows execution evidence remain missing.

## Blocks ENTERPRISE PRODUCTION READY

1. No load/heavy workflow evidence.
2. No trace persistence/export durability proof.
3. No cost/latency SLO evidence.
4. No operational support model.
5. No production incident/rollback playbook.
6. No broad repeated model/provider/schema matrix. A first live Leonardo HF-local matrix exists, but it is not broad/repeated enough and did not pass thresholds.
7. Enterprise compatibility matrix exists locally, but remote CI evidence and customer-environment validation are missing.
8. No third-party/formal privacy/security/compliance audit beyond local boundary docs, hygiene docs, classification tooling, and tests.

## Required blocker disposition

Every blocker must have:
- owner;
- severity;
- target readiness label;
- planned fix or evidence artifact;
- verification command;
- status;
- date closed.

## 2026-05-18 direct evidence disposition update

- Gate 1 update: GitHub Actions run `26011084310` completed successfully and validates as legacy Ubuntu remote CI evidence (`benchmarks/results/legacy_remote_ci_evidence_26011084310.json`). This does not close remote Windows/macOS matrix proof because the remote `main` workflow was still the old single-job workflow. Remaining request: push/run the updated matrix workflow, download the three matrix artifacts, and run `python scripts/assert_remote_ci_matrix_evidence.py --artifacts-dir benchmarks/results/remote_ci_artifacts --out benchmarks/results/remote_ci_matrix_evidence.json`.
- Gate 8 update: real Azure provider-classified serious-workflow evidence is now `PASS`. Evidence manifest: `benchmarks/results/serious_workflow_provider_evidence_azure_pass_candidate/manifest.json`; incident-response/runbook, fintech transaction-risk, and support-ticket triage each pass 8 provider rows. Remaining boundary: cross-provider serious-workflow replications are still needed for claims broader than the Azure pilot evidence.
- Gate 9 update: latest full local suite is `213 passed, 10 skipped`; focused external/product/release validation is `102 passed`. Remote three-OS CI matrix evidence is still open.
- Readiness label remains **PRODUCT READY for audited developer/software scope**, not Enterprise Pilot Ready, until remote three-OS matrix CI, broader passing provider/OSS/HPC matrix evidence, and formal compliance/security review are complete.