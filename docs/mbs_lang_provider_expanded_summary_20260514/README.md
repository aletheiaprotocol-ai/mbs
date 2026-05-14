# MBS-Lang Expanded Azure Provider Evidence — 2026-05-14

This package is a sanitized public summary of one real Azure provider MBS-Lang run against the expanded 15-row multilingual fixture surface.

## Evidence Boundary

This is **provider behavior evidence** only for:

- schema: `examples/multilingual_risk_review/schema.json`
- cases: `examples/multilingual_risk_review/cases.jsonl`
- rows: 15
- languages: `ar`, `de`, `en`, `es`, `fr`, `hu`, `tr`
- domains: `fintech`, `procurement`, `qme_source_review`, `support`, `tool_call_safety`
- model/deployment: `gpt-5-3-chat`
- mode: `json_mode`
- gate: `benchmarks/provider_lang_gate.example.yaml`
- run date: `2026-05-14`

It is not broad multilingual reliability evidence and it is not an independent translation-quality benchmark.

Raw provider outputs are not included in this public package. They remain in ignored local `results/` paths unless scrubbed and intentionally released.

## Result

| model | mode | gate | cases | traceable | schema | semantic | clean JSON | infra failures | top failure |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `gpt-5-3-chat` | `json_mode` | `FAIL` | 15 | 15 | 0.9333 | 0.9333 | 0.9333 | 1 | `content_filter:16` |

The run is an honest provider gate failure, not an MBS infrastructure failure: all 15 rows were traceable, but one Arabic tool-call-safety row triggered Azure provider content filtering. MBS preserved the failure as classified evidence instead of hiding it or turning it into a pass.

## Reproduce the Evidence Flow

With an authorized Azure OpenAI-compatible deployment configured:

```bash
python scripts/run_lang_provider_evidence.py \
  --model gpt-5-3-chat \
  --deployment gpt-5-3-chat \
  --classification provider \
  --mode json_mode \
  --out-dir results/mbs_lang_provider_evidence_azure_gpt_5_3_chat_20260514_expanded
```

## Interpretation

This expanded run shows that the 15-row MBS-Lang gate is stricter than the earlier historical seven-case provider summary. The expanded suite includes procurement, support, QME-style source review, and tool-call-safety rows in addition to fintech rows. The current result is useful negative evidence: provider filtering can affect multilingual structured-output evaluation even when trace coverage is complete.
