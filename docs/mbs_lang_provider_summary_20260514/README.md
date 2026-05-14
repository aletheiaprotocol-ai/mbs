# MBS-Lang Azure Provider Summary — 2026-05-14

This package is a sanitized public summary of one real Azure provider MBS-Lang evidence run.

## Evidence Boundary

This is **provider behavior evidence** only for:

- schema: `examples/multilingual_risk_review/schema.json`
- cases: `examples/multilingual_risk_review/cases.jsonl`
- languages: `ar`, `de`, `en`, `es`, `fr`, `hu`, `tr`
- model/deployment: `gpt-5-3-chat`
- mode: `json_mode`
- gate: `benchmarks/provider_lang_gate.example.yaml`
- run date: `2026-05-14`

It is not broad multilingual reliability evidence and it is not an independent translation-quality benchmark.

Raw provider outputs are not included in this public package. They remain in ignored local `results/` paths unless scrubbed and intentionally released.

## Result

| model | gate | cases | traceable | schema | semantic | clean JSON | infra failures | languages |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `gpt-5-3-chat` | `PASS` | 7 | 7 | 1.0 | 1.0 | 1.0 | 0 | ar/de/en/es/fr/hu/tr |

## Reproduce the Evidence Flow

With an authorized Azure OpenAI-compatible deployment configured:

```bash
python scripts/run_lang_provider_evidence.py \
  --model gpt-5-3-chat \
  --deployment gpt-5-3-chat \
  --provider azure \
  --endpoint "$AZURE_OPENAI_ENDPOINT" \
  --api-key-env AZURE_OPENAI_API_KEY \
  --classification provider \
  --mode json_mode \
  --gate-config benchmarks/provider_lang_gate.example.yaml \
  --out-dir results/mbs_lang_provider_evidence_azure_gpt_5_3_chat_20260514
```

## Interpretation

The run passed the configured multilingual provider gate with no infrastructure failures and complete trace coverage. This is useful provider evidence for the listed narrow task. The next evidence gate is to repeat the same flow across additional providers, OSS/HPC models, schemas, seeds, and languages.
