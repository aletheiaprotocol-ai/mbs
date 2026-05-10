# MBS Model Behavior Guidance

MBS model status is about structured agent output behavior, not general model quality.

## Status Rules

| status | meaning | product action |
| --- | --- | --- |
| PASS | The model produces valid structured output at high rates, with acceptable semantic correctness and low format risk. | Safe candidate for structured-output workflows after task-specific testing. |
| REVIEW | The model can often be made schema-valid, but has format or semantic risk that needs guardrails. | Use MBS validation, trace, retry, and clean-JSON monitoring before tool execution. |
| FAIL | The model repeatedly emits invalid JSON, reasoning prose, or semantically unsafe output for structured-agent tasks. | Do not use for direct structured tool calls unless a stronger constrained decoding layer fixes behavior. |

## Format Risk

MBS separates schema validity from clean output format.

- `clean_json_rate`: output is raw parseable JSON without relying on extraction.
- `prose_wrapped_json`: JSON can be recovered, but the model wraps it in markdown or text.
- `reasoning_prose`: the model emits analysis/reasoning instead of the requested JSON object.

A model can be schema-valid after extraction and still be a product risk. For agents, raw clean JSON matters because tool callers and workflow engines should not depend on brittle prose extraction.

## Current Signals

Strong PASS rows:

- Mixtral 8x22B Instruct: schema retry reaches `1.0`; MBS-Lang reaches `1.0` / `1.0`.
- OLMo 2 13B Instruct: clean schema/prompt retry and clean MBS-Lang behavior.
- Hermes 3 Llama 3.1 70B: schema retry reaches `1.0` schema-valid / `0.9167` semantic / `1.0` clean JSON; MBS-Lang reaches `1.0` / `1.0`.
- Qwen3-30B-A3B Instruct: schema retry reaches `1.0` schema-valid / `0.9167` semantic / `1.0` clean JSON; MBS-Lang reaches `1.0` / `1.0`.

Useful REVIEW rows:

- Falcon3 10B: high extracted schema validity, but low clean JSON due fenced/prose-wrapped outputs.
- MiniCPM4 8B: MBS-Lang retry can be schema-valid, but clean JSON remains low.
- Mistral Small 3.1 24B: schema/prompt retry reaches `1.0` schema-valid and MBS-Lang reaches `1.0`, but clean JSON remains low because outputs are commonly prose-wrapped.
- Nemotron 70B and Phi-3.5 MoE: strong semantic behavior in some settings, but prose wrapping requires explicit format monitoring.

Clear FAIL rows for direct structured-agent output:

- Qwen3 32B and QwQ 32B: reasoning/prose behavior keeps clean JSON at `0.0`.
- Phi-4 Reasoning Plus: retry does not recover schema-valid or semantic structured output in the current harness.
- DeepSeek R1 Distill Qwen rows: reasoning-prose behavior dominates in MBS-Lang and structured schema settings.
- DeepSeek R1 Distill Llama 70B: schema/prompt retry reaches only `0.4583` schema-valid / `0.5833` semantic and clean JSON remains `0.0`; MBS-Lang retry reaches only `0.4286` schema/semantic.

## Recommended Default

Use `full` contracts and semantic retry with conservative best-attempt adoption.

Use `strict` contracts as diagnostics for models that emit markdown, analysis, or prose around JSON. Strict contracts can expose whether the problem is contract clarity or model behavior, but strict alone does not make reasoning/prose model families safe.

## What To Measure Before Deployment

- schema-valid rate
- semantic correctness
- clean JSON rate
- retry count
- cost per valid output
- top failure types
- row-level regressions after retry
- trace ids for failures that could trigger tool calls
