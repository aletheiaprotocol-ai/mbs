# MBS Enterprise Blocker Disposition

## Status

This document assigns every remaining Enterprise Pilot/Production blocker an owner, severity, target readiness label, planned evidence artifact, verification command, status, and closure condition. It prevents readiness language from drifting ahead of evidence.

## Disposition table

| ID | Blocker | Owner | Severity | Target readiness label | Planned fix or evidence artifact | Verification command | Status | Closure condition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B-001 | Remote non-Windows CI run evidence is not captured | Release operator | High | Enterprise Pilot Ready | GitHub Actions run URL for `ubuntu-latest`, `windows-latest`, and `macos-latest` matrix | `gh run view <run-id> --log` or GitHub Actions UI artifact review | Open | All matrix legs pass and artifact bundle is retained |
| B-002 | Full CLI command matrix is incomplete | Product engineering | Medium | Enterprise Pilot Ready | `docs/mbs_cli_command_matrix_20260517.md` plus regression tests covering every public subcommand help and one success/failure path | `python -m pytest -q` plus saved command transcript summary | Closed locally | Transcript summary and regression tests cover all public commands; remote CI evidence remains B-001/B-009 |
| B-003 | JSON robustness matrix is incomplete | Product engineering | Medium | Enterprise Pilot Ready | Invalid inline/file JSON matrix covering schema, output, config, JSONL, request files, and BOM cases | `python -m pytest -q tests/test_mbs_conformance.py tests/test_mbs_product.py` | Closed locally | Negative cases fail without Python tracebacks; remote CI evidence remains B-001/B-009 |
| B-004 | Hard-schema validation is incomplete beyond current software fixtures | Product engineering | Medium | Enterprise Pilot Ready | `examples/adversarial_policy_execution/`, `scripts/run_adversarial_hard_schema_pack.py`, and `benchmarks/results/adversarial_hard_schema_pack/manifest.json` | `python -m pytest -q tests/test_adversarial_hard_schema_pack.py`; `python scripts/run_adversarial_hard_schema_pack.py --out-dir benchmarks/results/adversarial_hard_schema_pack --json` | Closed locally | Strict adversarial fixture pack passes good-output gates and intentionally bad-output failure/warning matrix; provider/OSS breadth remains B-007/B-008 |
| B-005 | Agent output contract is not enterprise-complete | Agent integration owner | Medium | Enterprise Pilot Ready | `docs/mbs_agent_tool_contract_v1.md` plus regression tests for versioned descriptors, success envelopes, error envelopes, output paths, and trace fields | `python -m pytest -q tests/test_mbs_product.py tests/test_ci_release_workflow.py` | Closed locally | Contract fields and failure envelopes are stable and documented; remote CI evidence remains B-001/B-009 |
| B-006 | Benchmark breadth is incomplete | Evaluation owner | High | Enterprise Pilot Ready | `scripts/run_multi_schema_fixture_bundle.py` builds a four-schema fixture benchmark bundle with trace coverage, cost-per-valid-output metrics, gate evidence, and classification manifest | `python scripts/run_multi_schema_fixture_bundle.py --out-dir benchmarks/results/multi_schema_fixture_bundle`; `python scripts/classify_release_artifacts.py benchmarks/results/multi_schema_fixture_bundle --repo-root . --fail-on-review` | Closed locally | Scoped fixture benchmark bundle passes gate and classification review; provider/OSS breadth remains B-007/B-008 |
| B-007 | Provider/OSS coverage is missing or too narrow | Evaluation owner | High | Enterprise Pilot Ready | Provider/OSS model matrix with raw outputs classified as provider/OSS evidence; scaffold now exists in `scripts/run_nested_provider_evidence.py`, including OpenAI-compatible, Ollama, and LM Studio dry-run plans. Safe local dry-run artifacts now exist for Ollama tiny/small, LM Studio, vLLM/OpenAI-compatible, and HPC placeholders. | `python scripts/run_nested_provider_evidence.py --dry-run --runner openai-compatible ...`; `python scripts/run_nested_provider_evidence.py --dry-run --runner ollama ...`; `python scripts/run_nested_provider_evidence.py --dry-run --runner lm-studio ...`; `python scripts/run_nested_provider_evidence.py --responses <jsonl> --classification provider|oss|hpc ...`; artifact classification | Open — scaffold closed locally, one Azure provider run captured, OSS/HPC live matrix pending | At least pilot model/provider matrix is captured and reviewed across the target provider/OSS families |
| B-008 | Real provider-classified workflow runs are missing | Evaluation owner | High | Enterprise Pilot Ready | Provider-classified runs for the serious workflow packs; nested-tool response-file evidence path now exists and blocks secret-bearing JSONL. Azure Sweden `gpt-5.5` nested tool-call evidence passed locally for 25 cases, but broader serious workflow/provider coverage is still pending. | `python scripts/run_nested_provider_evidence.py --responses <provider-jsonl> --classification provider ...`; `python scripts/classify_release_artifacts.py <provider-results> --repo-root .` | Open — one scoped Azure nested run captured and reviewed locally; real provider runs for the serious workflow packs still pending | Provider artifacts for the required serious workflows are reviewed and summarized without secrets/sensitive raw data |
| B-009 | Remote CI matrix run evidence remains incomplete | Release operator | High | Enterprise Pilot Ready | Matrix run URL and artifact bundle retained from `.github/workflows/mbs-ci.yml` | `gh run view <run-id> --log` or GitHub Actions UI artifact review | Open | Remote CI results are attached to release evidence |
| B-010 | Formal third-party compliance/security review is not complete | Compliance owner | High | Enterprise Pilot Ready | External review memo or signed internal risk acceptance referencing `docs/mbs_compliance_security_boundary.md` | Manual governance review | Open | Review is signed or explicitly waived by owner |
| B-011 | Load/heavy workflow evidence is missing | Evaluation owner | High | Enterprise Production Ready | Load or batch evidence bundle with latency/failure/cost metrics | To be defined with production scenario | Open | Load evidence meets target SLOs |
| B-012 | Trace persistence/export durability proof is missing | Product engineering | Medium | Enterprise Production Ready | Durable trace export/import proof and schema versioning tests | `python -m pytest -q` plus export/import transcript | Open | Trace artifacts round-trip and remain queryable |
| B-013 | Cost/latency SLO evidence is missing | Evaluation owner | Medium | Enterprise Production Ready | SLO report across representative workloads | `mbs report --results <results> --require-traces` | Open | Report includes cost/latency bounds and pass/fail thresholds |
| B-014 | Operational support model is missing | Operations owner | Medium | Enterprise Production Ready | Support runbook, incident escalation path, and maintenance ownership | Manual doc review | Open | Runbook approved and linked from release docs |
| B-015 | Production incident/rollback playbook is missing | Operations owner | Medium | Enterprise Production Ready | Incident/rollback playbook for package and evidence releases | Manual doc review | Open | Playbook approved and rehearsed |
| B-016 | Broad repeated model/provider/schema matrix is missing | Evaluation owner | High | Enterprise Production Ready | Repeated-run benchmark matrix with confidence intervals and drift checks | `mbs report`, `mbs gate`, and artifact classification | Open | Matrix evidence supports production reliability claims |
| B-017 | Customer-environment validation is missing | Pilot owner | Medium | Enterprise Pilot Ready | Customer/pilot environment validation note for OS, Python, shell, secrets, and provider config | Pilot-specific smoke test transcript | Open | Pilot environment passes install, CLI, and evidence-gate smoke tests |

## Current safe readiness language

Allowed now:

- "Local release hygiene checks passed."
- "Package build, package inspection, fresh install proof, and artifact classification passed locally."
- "Cross-platform CI is configured and regression-guarded for Ubuntu, Windows, and macOS."
- "Local multi-schema fixture benchmark breadth evidence passed gate and classification review."
- "Local adversarial hard-schema fixture evidence passed good/bad validation gates."
- "Nested provider/OSS/HPC evidence scaffolding is implemented and regression-guarded locally, including dry-run plans, response-file reuse, classification, gates, evidence packs, and secret blocking."
- "One scoped Azure Sweden `gpt-5.5` nested tool-call provider run passed locally with 25 traceable rows, zero infrastructure failures, and review-required provider artifact classification."
- "The transport-neutral agent-tool contract is versioned and regression-guarded locally."

Not allowed yet:

- "Enterprise Pilot Ready"
- "Enterprise Production Ready"
- "Compliance certified"
- "All provider evidence is public-safe"

## Maintenance rule

Every new readiness blocker must be added to the table before a readiness label is changed. A blocker can be closed only when its verification command or manual review evidence is recorded in the release evidence bundle.
