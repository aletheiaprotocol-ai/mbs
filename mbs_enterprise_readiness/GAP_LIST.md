# Enterprise Gap List

## Critical product gaps

1. Full cross-platform fresh install evidence is missing.
2. Full CLI command matrix is missing.
3. Complete JSON robustness matrix is missing.
4. Full hard-schema validation matrix is missing.
5. Enterprise output contract for agent tool calls is incomplete or unproven.
6. No persistent trace export/durability proof.
7. No enterprise integration docs.

## Evidence gaps

1. Broad model-family benchmark evidence is missing.
2. Weight-scale evidence is missing.
3. Quantized vs non-quantized evidence is missing.
4. Closed-provider matrix is missing except Azure `gpt-5.5`.
5. OSS local/HPC matrix is missing.
6. Retry/no-retry comparisons are missing.
7. Cost per valid output is missing.
8. Cost per semantically correct output is missing.
9. Latency distributions are missing.
10. Failure taxonomy at row level is incomplete for enterprise use.

## Workflow gaps

1. Incident response/runbook review pack missing.
2. Fintech/support/compliance workflow pack missing.
3. QME/medical-legal/source-grounded workflow pack missing.
4. Cybersecurity triage pack missing.
5. Procurement/HR/policy exception packs missing.
6. Agent tool-call safety pack missing.
7. Memory-write admission pack missing.
8. Multilingual structured-output pack missing.

## Security/privacy/release gaps

1. Secret scan artifact missing.
2. Public test data safety review missing.
3. Huge-file/artifact audit missing.
4. Dependency/license scan missing.
5. Hosted demo boundary review missing.
6. Data retention/export statement missing.
7. Enterprise privacy/security statement missing.

## Documentation gaps

1. Enterprise CI integration guide missing.
2. Provider configuration matrix missing.
3. Failure taxonomy guide missing.
4. Retry policy guide missing.
5. Trace export guide missing.
6. Security/privacy guide missing.
7. Limitations and known-failures page missing.

## Blocking gaps by readiness label

### Blocks ENTERPRISE PILOT READY

- Missing hard workflow packs.
- Missing broad enough model/provider matrix.
- Missing CI regression guard expansion.
- Missing release hygiene audit.
- Missing enterprise docs.

### Blocks ENTERPRISE PRODUCTION READY

- Missing heavy workflow/load evidence.
- Missing trace persistence/export durability.
- Missing cost/latency SLO evidence.
- Missing operational playbooks.
- Missing SLA/support model.
- Missing broad production-like provider/OSS evidence.