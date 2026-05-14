# MBS-Lang

MBS-Lang separates the compact structured-output contract from the user language.

The default pattern is:

```text
input language: local user language
contract language: compact schema/key language
output language: local free-text fields
```

## Arabic Example

```bash
mbs lang examples/multilingual_risk_review/schema.json \
  --input-language ar \
  --output-language ar \
  --contract-language en
```

## Turkish Example

```bash
mbs lang examples/multilingual_risk_review/schema.json \
  --input-language tr \
  --output-language tr \
  --contract-language en
```

## Why It Matters

Structured fields and enum values should stay stable and compact. Free-text explanation fields can remain in the user's language. Benchmarks should compare token cost and reliability with a Token Fairness Ratio instead of treating every language as the same prompt problem.

The Python helper returns `token_fairness_ratio` and `english_baseline_tokens` for local reporting.

## Fixture Matrix

Run the deterministic fixture matrix to verify wrapper instructions, English schema-key/enum boundaries, and Token Fairness Ratio reporting:

```bash
python scripts/run_mbs_lang_matrix.py --out-dir results/mbs_lang_matrix_fixture
```

The current fixture-classified matrix is summarized in `docs/mbs_lang_matrix.md`. It is contract-surface evidence only, not provider/model behavior or translation-quality evidence.

## Provider/OSS/HPC Evidence Flow

Use the provider evidence runner to collect or reuse multilingual response rows and build a classified evidence pack:

```bash
python scripts/run_lang_provider_evidence.py \
  --responses results/mbs_lang_provider.responses.jsonl \
  --model provider-or-oss-model-id \
  --classification provider \
  --mode json_mode \
  --out-dir results/mbs_lang_provider_evidence
```

For local fixture-path validation only:

```bash
python scripts/run_lang_provider_evidence.py \
  --responses examples/multilingual_risk_review/provider_json_mode_good.jsonl \
  --model fixture-lang-provider \
  --classification fixture \
  --mode json_mode \
  --out-dir results/mbs_lang_provider_evidence
```

Use `--dry-run` without `--responses` to write the planned provider collection command without calling any provider. Real provider/OSS/HPC claims require classified result JSON, report, gate, triage, manifest, and trace coverage.
