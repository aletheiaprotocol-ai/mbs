# MBS-Lang Fixture Matrix

Classification: `fixture_mbs_lang_matrix_not_provider_benchmark`

This deterministic fixture matrix proves the MBS-Lang contract surface:

- local-language input wrapper is present;
- English schema-key and enum boundary is preserved;
- free-text output-language wrapper is present;
- Token Fairness Ratio and English baseline accounting are reported;
- schema-valid, semantic correctness, language mismatch, and cost-per-valid-output accounting are reported for deterministic fixture outputs.

It does **not** prove provider/model reliability, OSS/HPC behavior, or translation quality.

## Reproduce

```bash
python scripts/run_mbs_lang_matrix.py --out-dir results/mbs_lang_matrix_fixture
```

## Current Fixture Summary

- Languages: `ar`, `de`, `en`, `es`, `fr`, `hu`, `tr`
- Domains: `fintech`, `procurement`, `qme_source_review`, `support`, `tool_call_safety`
- Rows: `15`
- Case files: `7`
- Token Fairness Ratio range: `1.0 - 1.0`
- Average Token Fairness Ratio: `1.0`
- Schema-valid rate: `1.0`
- Semantic correctness rate: `1.0`
- Language mismatch rate: `0.0`
- Cost per valid output tokens: `101.733`
- Contract boundary failures: `0`

## Rows

| case | domain | input | output | contract | schema | semantic | language mismatch | TFR | boundary |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `ml_ar_001` | fintech | ar | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_ar_tool_002` | tool_call_safety | ar | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_de_001` | fintech | de | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_de_support_002` | support | de | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_en_high_001` | fintech | en | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_en_low_001` | fintech | en | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_en_qme_002` | qme_source_review | en | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_es_001` | fintech | es | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_es_procurement_002` | procurement | es | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_fr_001` | fintech | fr | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_fr_qme_002` | qme_source_review | fr | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_hu_001` | fintech | hu | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_hu_procurement_002` | procurement | hu | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_tr_001` | fintech | tr | en | en | PASS | PASS | no | 1.0 | PASS |
| `ml_tr_support_002` | support | tr | en | en | PASS | PASS | no | 1.0 | PASS |

## Evidence Boundary

This is deterministic fixture evidence for contract compilation and reporting. Real multilingual provider, OSS, or HPC model behavior must be generated from response rows and classified separately.