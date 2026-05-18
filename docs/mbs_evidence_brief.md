# MBS Evidence Brief

## Problem

Agents increasingly call tools, fill forms, and trigger workflows, but their structured outputs still fail in ordinary ways: invalid JSON, missing required fields, wrong enum values, and silent semantic drift. Teams usually discover these failures after the agent has already taken an action.

## Wedge

MBS compiles a schema into a minimal behavioral contract, validates model output, records a trace, and reports cost per valid structured output. The initial product is not a full agent platform; it is a small reliability layer for structured agent behavior.

## 30-Second Demo

Input: support-ticket schema + prompt about possible account takeover. The mock model returns `action=ANSWER|ESCALATE` and `priority=high`. MBS returns `FAIL` with failure type `invalid_enum`, trace `mbs_trace_918be14603a8`, and a targeted enum repair. The repaired output passes with trace `mbs_trace_efb9aecbdd70`.

## Sample Result

| strategy | schema-valid | semantic-correct | avg retries | cost / valid output |
| --- | ---: | ---: | ---: | ---: |
| verbose prompt | 0.500 | 0.500 | 0.000 | 385.0 |
| MBS contract + retry | 1.000 | 1.000 | 0.333 | 121.833 |

## Why It Matters

MBS turns a vague prompt-quality problem into measurable software behavior: PASS / FAIL / REVIEW, exact failure reasons, trace ids, retry counts, and cost per valid output. The short-term wedge is CI and evaluation for structured agent outputs. Future direction: consume these traces inside larger agent systems after external users validate the narrow product.
