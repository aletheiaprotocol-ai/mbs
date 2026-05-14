# MBS-Lang Fixture Matrix

Classification: `fixture_mbs_lang_matrix_not_provider_benchmark`

This deterministic fixture matrix proves the MBS-Lang contract surface:

- local-language input wrapper is present;
- English schema-key and enum boundary is preserved;
- free-text output-language wrapper is present;
- Token Fairness Ratio and English baseline accounting are reported.

It does **not** prove provider/model reliability, OSS/HPC behavior, or translation quality.

## Reproduce

```bash
python scripts/run_mbs_lang_matrix.py --out-dir results/mbs_lang_matrix_fixture
```

## Current Fixture Summary

- Languages: `ar`, `de`, `en`, `es`, `fr`, `hu`, `tr`
- Rows: `8`
- Case files: `7`
- Token Fairness Ratio range: `1.0 - 1.0`
- Average Token Fairness Ratio: `1.0`
- Contract boundary failures: `0`

## Rows

| case | input | output | contract | tokens | English baseline | TFR | boundary |
|---|---:|---:|---:|---:|---:|---:|---|
| `ml_ar_001` | ar | en | en | 62 | 62 | 1.0 | PASS |
| `ml_de_001` | de | en | en | 62 | 62 | 1.0 | PASS |
| `ml_en_high_001` | en | en | en | 62 | 62 | 1.0 | PASS |
| `ml_en_low_001` | en | en | en | 62 | 62 | 1.0 | PASS |
| `ml_es_001` | es | en | en | 62 | 62 | 1.0 | PASS |
| `ml_fr_001` | fr | en | en | 62 | 62 | 1.0 | PASS |
| `ml_hu_001` | hu | en | en | 62 | 62 | 1.0 | PASS |
| `ml_tr_001` | tr | en | en | 62 | 62 | 1.0 | PASS |

## Evidence Boundary

This is deterministic fixture evidence for contract compilation and reporting. Real multilingual provider, OSS, or HPC model behavior must be generated from response rows and classified separately.