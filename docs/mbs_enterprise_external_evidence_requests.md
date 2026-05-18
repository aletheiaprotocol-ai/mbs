# MBS Enterprise External Evidence Requests

These items cannot be completed by local code changes alone. They require remote
execution, credentials, third-party review, or additional provider/HPC runs.

## Remote CI matrix execution evidence

Request: run `.github/workflows/mbs-ci.yml` on GitHub Actions for the target
commit and download all three artifacts:

- `mbs-ci-artifacts-ubuntu-latest-py3.11`
- `mbs-ci-artifacts-windows-latest-py3.11`
- `mbs-ci-artifacts-macos-latest-py3.11`

Place them under `benchmarks/results/remote_ci_artifacts/` and verify with:

`python scripts/assert_remote_ci_matrix_evidence.py --artifacts-dir benchmarks/results/remote_ci_artifacts --out benchmarks/results/remote_ci_matrix_evidence.json`

## Provider-classified serious workflow runs

Request: collect reviewed, non-secret provider response JSONL for each workflow:

- `incident_response_runbook.jsonl`
- `fintech_transaction_risk.jsonl`
- `support_ticket_triage.jsonl`

Place them under `benchmarks/results/serious_workflow_provider_responses/` and verify with:

`python scripts/run_serious_workflow_provider_evidence.py --model <provider-model> --responses-dir benchmarks/results/serious_workflow_provider_responses --out-dir benchmarks/results/serious_workflow_provider_evidence --classification provider --mode tool_call`

Dry-run collection plan:

`python scripts/run_serious_workflow_provider_evidence.py --model <provider-model> --out-dir benchmarks/results/serious_workflow_provider_plan --classification provider --mode tool_call --dry-run`

## Broader OSS/HPC/closed-provider matrix

Request: run additional reviewed provider/OSS/HPC response collection for more
families, seeds, temperatures, and serious workflows. Do not claim Enterprise
Pilot Ready until gate-passing behavior evidence exists beyond the current
failing Leonardo runs and scoped Azure run.

## Formal compliance/security review

Request: obtain external review covering privacy, security, data retention,
artifact sensitivity, vulnerability reporting, and enterprise procurement. Local
docs and tests are not a third-party audit.

Minimum output artifact: a dated review letter or assessment report that may be
referenced from `docs/mbs_compliance_security_boundary.md` without exposing
confidential details.