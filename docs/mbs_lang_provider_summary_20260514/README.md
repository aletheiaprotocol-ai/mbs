# MBS-Lang Azure Provider Matrix — 2026-05-14

This package is a sanitized public summary of three real Azure provider MBS-Lang evidence runs.

## Evidence Boundary

This is **provider behavior evidence** only for:

- schema: `examples/multilingual_risk_review/schema.json`
- cases: `examples/multilingual_risk_review/cases.jsonl`
- languages: `ar`, `de`, `en`, `es`, `fr`, `hu`, `tr`
- model/deployments: `gpt-5-3-chat`, `gpt-4-1-nano`, `gpt-5-nano`
- mode: `json_mode`
- gate: `benchmarks/provider_lang_gate.example.yaml`
- run date: `2026-05-14`

It is not broad multilingual reliability evidence and it is not an independent translation-quality benchmark.

Raw provider outputs are not included in this public package. They remain in ignored local `results/` paths unless scrubbed and intentionally released.

## Results

| model | gate | cases | traceable | schema | semantic | clean JSON | infra failures | languages |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `gpt-5-3-chat` | `PASS` | 7 | 7 | 1.0 | 1.0 | 1.0 | 0 | ar/de/en/es/fr/hu/tr |
| `gpt-4-1-nano` | `PASS` | 7 | 7 | 1.0 | 1.0 | 1.0 | 0 | ar/de/en/es/fr/hu/tr |
| `gpt-5-nano` | `FAIL` | 7 | 7 | 0.0 | 0.0 | 0.0 | 0 | ar/de/en/es/fr/hu/tr |

The `gpt-5-nano` row is an honest provider gate failure, not an infrastructure failure: all seven rows were traceable and classified as `invalid_json` under this JSON-mode contract.

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

Two deployments passed the configured multilingual provider gate, and one deployment failed cleanly on format/schema behavior with no infrastructure failures. This is useful provider evidence for the listed narrow task. The next evidence gate is to repeat the same flow across additional providers, OSS/HPC models, schemas, seeds, and languages.
