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
