# MBS Copilot Project Instructions

This repo is MBS, a serious Software for Agents product.

The user does not want more planning-only work. The user wants execution.

Default behavior:
- Do not stop after one small task.
- Do not only create markdown plans.
- Execute safe local tasks until the batch target is complete or genuinely blocked.
- If a task fails, fix it immediately, rerun tests, and continue.
- If blocked on paid API, remote HPC/cloud jobs, credentials, public deployment, deletion, secrets, or legal/security risk, mark that task BLOCKED and continue the next safe local task.
- Do not ask “what next” while safe local tasks remain.

Primary working files:
- mbs_enterprise_readiness/NEXT_50_TASKS.md
- mbs_enterprise_readiness/BUG_FIX_QUEUE.md
- mbs_enterprise_readiness/RELEASE_BLOCKERS.md
- mbs_enterprise_readiness/ENTERPRISE_READINESS_SCORECARD.md

Execution priority:
1. Real product bugs
2. Clean install and quickstart
3. Controlled CLI errors
4. Machine-readable CLI/API/agent outputs
5. External-user smoke test
6. Agent workflow demo
7. Hard workflow fixtures
8. CI/regression gates
9. Provider/model evidence
10. Security/release hygiene

Every task must produce evidence:
- files changed
- commands run
- tests run
- pass/fail result
- artifact path
- readiness status update

Do not mark MBS enterprise-ready without evidence.
