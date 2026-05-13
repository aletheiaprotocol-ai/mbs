# MBS MN5 vs Azure 40-Case Comparison — May 2026

This report compares two evidence streams for the same hard structured
support-routing fixture. It is not a universal model leaderboard. It is a
product evidence note showing that MBS can compare structured-output behavior
across closed providers and open-source models while preserving infra/behavior
separation.

## Shared Fixture

- Schema: `examples/hard_agent_routing/schema.json`
- Cases: `examples/hard_agent_routing/cases.jsonl`
- Case count: 40
- Task: choose a structured support-routing action, priority, human escalation
  flag, customer visibility flag, risk tags, and rationale.

The fixture is hard enough to fail: all evaluated systems produced either
format failures, semantic mismatches, or both.

## Closed Provider Matrix

Azure OpenAI deployments were run across text, JSON mode, and tool-call modes:

| model | modes | runs | infra failures | schema valid | semantic correct | clean JSON | top failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `gpt-5.5` | 3 | 120 | 0 | 1.0000 | 0.3250 | 1.0000 | `semantic_mismatch:81` |
| `gpt-5-nano` | 3 | 120 | 0 | 0.0333 | 0.0167 | 0.0333 | `invalid_json:116`, `semantic_mismatch:2` |

Mode detail for `gpt-5.5`:

- JSON mode: semantic-correct `0.4000`
- text: semantic-correct `0.3500`
- tool-call: semantic-correct `0.2250`

## MN5 OSS Matrix

MN5 local Hugging Face jobs were run in `hf_local_json_mode` on cached models:

| model | rows | infra failures | JSON valid | schema valid | semantic correct | top failures |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `Qwen2.5-7B-Instruct` | 40 | 0 | 1.0000 | 0.9250 | 0.2250 | `semantic_mismatch:28`, `invented_enum:3` |
| `Qwen2.5-14B-Instruct` | 40 | 0 | 1.0000 | 0.9500 | 0.2000 | `semantic_mismatch:30`, `invented_enum:2` |
| `Mistral-7B-Instruct-v0.3` | 40 | 0 | 1.0000 | 0.8250 | 0.2000 | `semantic_mismatch:28`, `invented_enum:7` |
| `Llama-3.1-8B-Instruct` | 40 | 0 | 0.0000 | 0.0000 | 0.0000 | `invalid_json:40` |

## Cross-Provider Takeaways

1. Schema validity and semantic correctness diverge sharply. `gpt-5.5`, Qwen,
   and Mistral can often produce valid schemas while still choosing the wrong
   routing decision or policy flags.
2. Tool calling did not automatically solve semantic routing for `gpt-5.5`; in
   this fixture, JSON mode and text mode beat tool calling on semantic accuracy.
3. Smaller or weaker deployments can be format-limited before semantic behavior
   is measurable. `gpt-5-nano` and the tested Llama collector/prompt path mostly
   failed at the JSON/schema layer.
4. MBS produces actionable failure clusters: invalid JSON, invented enum values,
   and semantic mismatches are distinct product/debugging signals.

## What Can Be Claimed

- MBS can run real structured-output provider tests, not only local validators.
- MBS can compare closed and OSS model behavior on the same audited contract.
- MBS separates infrastructure failures from behavior evidence.
- MBS exposes semantic failures that JSON validation alone would miss.

## What Cannot Be Claimed Yet

- No universal model ranking.
- No claim that a provider or OSS family is generally reliable/unreliable.
- No claim that tool calling is generally worse than JSON mode.
- No fine-tuning claim until repeated runs, reviewed labels, and additional
  model families confirm stable failure clusters.

## Next Evidence Steps

- Run the expanded MN5 submitter on every cached model family.
- Add prompt/mode variants for Llama to separate collector formatting mismatch
  from model capability.
- Review controversial expected labels and document policy precedence.
- Use `scripts/analyze_mbs_failures.py` after each run to compare recurring
  case-level failure clusters.