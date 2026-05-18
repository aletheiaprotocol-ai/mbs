# MBS Enterprise Readiness Plan

## Mission

MBS must become enterprise-grade software for agent structured-output reliability work. The target is not a scoped benchmark pass or a CLI demo. The target is durable company usage for heavy agent workflows where structured outputs, validation, traces, failure reasons, retry behavior, benchmarks, CI gates, and auditability matter.

## Current readiness label

**Current label: PRODUCT READY for the audited developer/software surface only.**

MBS is **not yet ENTERPRISE PILOT READY** and is **not ENTERPRISE PRODUCTION READY**. The current evidence proves installability, core CLI/API behavior, trace/report generation, CI artifact generation, and one live Azure `gpt-5.5` nested benchmark passing the configured gate in three modes. It does not yet prove broad company-grade reliability across model families, provider modes, hard schemas, retries, security/privacy requirements, or heavy workflows.

## Enterprise target labels

- **NOT READY**: install, CLI, validation, traces, or docs fail.
- **EARLY READY**: works locally for technical testers, but not production/company-grade.
- **PRODUCT READY**: external developers can install, use, validate outputs, create traces, run tests, and integrate in simple agent workflows with clear docs and controlled failures.
- **ENTERPRISE PILOT READY**: real teams can use MBS in limited workflows with audit trails, CI gates, known limits, broad evidence, and supportable failure modes.
- **ENTERPRISE PRODUCTION READY**: broad model/provider/schema evidence, robust error handling, security/release hygiene, CI integration, trace persistence/export, documented SLAs/limits, and realistic heavy-workflow testing.

## What is actually ready now?

- Clean editable install in the audited environment.
- Core package import and version reporting.
- CLI command discovery and basic help.
- Core `compile`, `validate`, `check`, `trace`, demo, benchmark/report paths in the audited flow.
- Python API for `compile`, `validate`, `check`, and `trace` in audited examples.
- Agent-callable CLI JSON wrapper for audited request patterns, including UTF-8 BOM input handling.
- CI fixture artifact assertion.
- Live Azure `gpt-5.5` nested evidence for `text`, `json_mode`, and `tool_call` modes with configured gate pass.
- Basic traceability, report generation, and failure classification for current benchmark artifacts.

## What is only partially ready?

- Provider evidence: real but narrow; one Azure deployment and one nested schema/case family.
- Semantic correctness: above current threshold, but still has mismatches.
- Retry behavior: not yet broadly measured across no retry, one retry, failure-specific retry, semantic retry, and human-review routing.
- Agent-tool reliability: present as a callable interface, not yet validated under complex real workflows.
- Docs: useful for current product surface, not yet enterprise integration/runbook docs.
- Security/release hygiene: needs formal secret scan, data audit, license review, and hosted-demo boundary review.
- Cross-platform quickstart: Windows audited; Linux/macOS need repeatable fresh-environment proof.

## What is not ready?

- Enterprise pilot claim.
- Enterprise production claim.
- Broad model-family reliability claim.
- Broad provider-mode reliability claim.
- Heavy production workflow claim.
- Cost/latency reliability claim.
- SLA/supportability claim.
- Security/privacy compliance claim.
- Persistent trace export/retention claim unless separately implemented and tested.

## What blocks real company usage?

- Missing broad, repeatable model/provider/schema evidence.
- Missing hard workflow replay packs.
- Missing retry/no-retry regression maps.
- Missing cost per valid and cost per semantically correct output.
- Missing latency distributions.
- Missing source-grounded citation correctness tests.
- Missing security/privacy/release hygiene audit artifacts.
- Missing enterprise docs for CI gates, trace export, integration patterns, and failure response.

## What blocks paid usage?

- No support model, compatibility matrix, or published limits.
- No enterprise onboarding guide.
- No license/commercial-use review artifact.
- No security statement or data handling statement.
- No versioned benchmark matrix across representative models/providers.
- No release process proving no secrets, no unsafe data, no accidental huge artifacts.

## What blocks heavy production usage?

- No load/scale evidence.
- No trace storage/export durability evidence.
- No long-running regression evidence.
- No failure-mode SLOs or operational playbooks.
- No production-grade provider adapter matrix.
- No hard adversarial benchmark gate across real schemas.
- No documented rollback/incident process for benchmark or validation regressions.

## Execution strategy

1. Fix product bugs found during manual testing first, including all remaining Windows/BOM/JSON file and output edge cases.
2. Expand deterministic local tests for validation, traces, CLI JSON output, and errors.
3. Build hard workflow schema packs and adversarial case packs.
4. Run broad local/OSS model-family evidence using vLLM/Ollama/LM Studio/OpenAI-compatible endpoints.
5. Run selected HPC weight-scale evidence with cached models and reproducible job manifests.
6. Run closed-provider evidence for available Azure/OpenAI/Anthropic/Gemini/Cohere deployments.
7. Produce failure maps, retry maps, cost/latency summaries, and scorecards.
8. Promote only when enterprise gates pass with artifacts.

## Promotion rule

MBS cannot be called **ENTERPRISE PILOT READY** until every Gate 1-10 pilot requirement in `ENTERPRISE_GATES.md` is passed or explicitly waived with owner, reason, expiry, and risk.

MBS cannot be called **ENTERPRISE PRODUCTION READY** until the production scorecard has broad provider/model/schema evidence, security/release hygiene, trace export durability, CI regression behavior, and realistic heavy-workflow testing.