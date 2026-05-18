# Hard Schema Plan

## Goal

Replace toy-only structured-output testing with serious schemas that resemble real enterprise agent workflows.

## Required schema packs

1. **Fintech transaction risk**
   - risk score, category, evidence, escalation, human-review flag.
2. **Support escalation**
   - issue class, severity, allowed action, missing info, escalation route.
3. **Incident response/runbook review**
   - incident type, impact, mitigation steps, unsafe action detection, confidence.
4. **Medical-legal/QME review**
   - source-grounded findings, unsupported claim flags, review-required routing.
5. **Procurement approval**
   - policy thresholds, approvals, exception reasons, vendor risk.
6. **Compliance policy exception**
   - policy ID, exception type, allowed/denied decision, compensating controls.
7. **Cybersecurity incident triage**
   - severity, indicators, containment, false-positive flag, escalation.
8. **HR workflow/risk triage**
   - risk type, protected-class sensitivity flag, human-review route.
9. **Agent tool-call safety**
   - proposed tool, arguments, allowed/blocked, safety reason.
10. **Memory-write admission**
   - memory type, retention, sensitivity, allowed/blocked, redaction.
11. **Source-grounded claim review**
   - claims, citations, support status, unsupported/fake citation flags.
12. **Multilingual structured output**
   - input language, output language, normalized enums, translation-sensitive fields.
13. **Nested multi-action planning**
   - ordered actions, dependencies, preconditions, rollback steps.
14. **Policy-following decision**
   - policy version, decision, conflicts, stale-policy detection.
15. **Audit packet generation**
   - evidence bundle, trace IDs, failure reasons, approval state.

## Required case types per schema

- good case;
- bad case;
- ambiguous case;
- adversarial case;
- prompt-injection case;
- conflicting-policy case where relevant;
- missing-data case;
- refusal/should-review case.

## Required failure cases

- invalid JSON;
- markdown-wrapped JSON;
- prose around JSON;
- missing required keys;
- wrong types;
- extra keys;
- invalid enum;
- invented enum;
- enum casing error;
- joined enum alternatives;
- nested object failure;
- array item failure;
- schema-valid but semantically wrong output;
- unsupported claim;
- fake source citation;
- prompt injection;
- refusal;
- overlong output;
- language mismatch;
- missing human-review flag;
- unsafe action marked allowed;
- stale policy followed;
- conflicting policy ignored;
- tool-call arguments wrong;
- correct JSON but wrong decision.

## Artifact requirements

Each schema pack must include:
- `schema.json`;
- `cases.jsonl`;
- `policy.md` where applicable;
- `expected_behavior.jsonl` or equivalent semantic oracle;
- README with domain limitations;
- benchmark config;
- report template;
- failure taxonomy mapping.