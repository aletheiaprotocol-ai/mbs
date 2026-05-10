# MBS YC Evidence Brief

## Problem

Agents increasingly call tools, fill forms, and trigger workflows, but their structured outputs still fail in ordinary ways: invalid JSON, missing required fields, wrong enum values, and silent semantic drift. Teams usually discover these failures after the agent has already taken an action.

## Wedge

MBS compiles a schema into a minimal behavioral contract, validates model output, records a trace, and reports cost per valid structured output. It also exposes model-specific failure behavior such as prose-wrapped JSON and reasoning text instead of JSON. The initial product is not a full agent platform; it is a small reliability layer for structured agent behavior.

## 30-Second Demo

Input: support-ticket schema + prompt about possible account takeover. The mock model returns `action=ANSWER|ESCALATE` and `priority=high`. MBS returns `FAIL` with failure type `invalid_enum`, trace `mbs_trace_ea5b06dfb86c`, and a targeted enum repair. The repaired output passes with trace `mbs_trace_48c5a4c12b8f`.

## Sample Result

Small deterministic demo:

| strategy | schema-valid | semantic-correct | avg retries | cost / valid output |
| --- | ---: | ---: | ---: | ---: |
| verbose prompt | 0.500 | 0.500 | 0.000 | 385.0 |
| MBS contract + retry | 1.000 | 1.000 | 0.333 | 121.833 |

GPU benchmark snapshot, MN5, 18 open instruction/chat/code/MoE models, 4 schemas, 7 MBS-Lang settings:

| benchmark | no-retry schema-valid | retry schema-valid | no-retry semantic | retry semantic | audit |
| --- | ---: | ---: | ---: | ---: | --- |
| schema/prompt | 0.7321 | 0.9388 | 0.8370 | 0.9203 | compare PASS; retry audit finds 1 Mixtral tool-call regression |
| MBS-Lang | 0.9061 | 0.9603 | 0.8783 | 0.9550 | PASS, 0 selected-attempt regressions |

Wider stress set after adding Phi-4 Mini, DeepSeek R1 Distill Qwen 14B, and DeepSeek R1 Distill Qwen 32B: schema/prompt retry reaches `0.8724` schema-valid and `0.8605` semantic over 21 models; MBS-Lang retry reaches `0.8639` schema-valid and `0.8594` semantic. DeepSeek is a clear FAIL row because it often emits reasoning prose instead of JSON, while Nemotron and Phi-3.5 MoE are schema-valid but expose `prose_wrapped_json` behavior for product hardening.

New large-model evidence: Mixtral 8x22B, OLMo 2 13B, Hermes 3 Llama 3.1 70B, and Qwen3-30B-A3B are strong PASS rows. Hermes 3 70B and Qwen3-30B-A3B both reach `1.0` schema-valid / `0.9167` semantic / `1.0` clean JSON on schema/prompt retry, and `1.0` / `1.0` / `1.0` on MBS-Lang retry. Falcon3 10B, MiniCPM4 8B, and Mistral Small 3.1 24B are useful REVIEW rows: retry can make many outputs schema-valid, but clean JSON stays low because the models wrap JSON in markdown/prose. Qwen3 32B, QwQ 32B, Phi-4 Reasoning Plus, and DeepSeek R1 Distill Llama 70B are clear structured-output FAIL rows: retry improves some extracted schema validity on reasoning models, but clean JSON remains `0.0` because the models emit reasoning/prose. This is the product point: MBS does not just show averages; it tells users which model behavior is unsafe for structured agents.

Product hardening metric: MBS now reports `clean_json_rate` and `format_risk`, separating raw JSON compliance from JSON recovered by extraction. The 18-model retry headline reaches `0.8810` clean JSON for schema/prompt and `0.9021` for MBS-Lang. Schema-valid but prose-wrapped models are labeled `REVIEW`; reasoning-prose models with poor clean JSON are labeled `FAIL`.

## Why It Matters

MBS turns a vague prompt-quality problem into measurable software behavior: PASS / FAIL / REVIEW, exact failure reasons, trace ids, retry counts, and cost per valid output. The short-term wedge is CI and evaluation for structured agent outputs. Future direction: consume these traces inside larger agent systems after external users validate the narrow product.
