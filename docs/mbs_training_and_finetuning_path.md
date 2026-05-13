# MBS Training And Fine-Tuning Decision Path

Fine-tuning should be a last-mile response after MBS has separated format, schema, infrastructure, and semantic failures.

## Decision Rules

Do not fine-tune when the main failure is:

- missing provider deployment;
- API timeout;
- too-small output token budget;
- text-mode JSON formatting failure that JSON/tool mode fixes;
- prompt ambiguity;
- schema design ambiguity.

Consider fine-tuning only when:

1. the same semantic failures persist across repeated hard cases;
2. infrastructure failures are zero or excluded;
3. JSON/tool modes produce schema-valid outputs;
4. expected labels are stable and reviewable;
5. failures are business/task decisions, not formatting problems.

## MBS Fine-Tuning Dataset Shape

Each training row should keep the MBS case identity and expected structured output:

```json
{
  "case_id": "hard_004",
  "input": "Customer says they accidentally bought the wrong plan five minutes ago and wants money back.",
  "expected_output": {
    "action": "REFUND_REQUEST",
    "priority": "MEDIUM",
    "requires_human": false,
    "customer_visible": true,
    "risk_tags": ["refund"],
    "rationale": "Recent accidental purchase should enter refund flow."
  }
}
```

## Evaluation Gate After Tuning

Create reviewable candidate rows from MBS failures with:

```powershell
python scripts\make_tuning_dataset.py `
  --mbs-result results\hard_agent_routing\provider.mbs.json `
  --cases examples\hard_agent_routing\cases.jsonl `
  --schema examples\hard_agent_routing\schema.json `
  --out results\training\hard_agent_routing_candidates.jsonl
```

The generator excludes infrastructure failures and emits only cases with stable
`expected_valid_outputs`. Generated rows are not final training data until a
human reviewer marks them approved.

A tuned model must beat the untuned baseline on:

- schema-valid rate;
- semantic-correct rate;
- cost per valid output;
- retry rate if retries are enabled;
- no regression on unrelated schemas.

## Current May 2026 Status

The Azure hard benchmark does not justify immediate fine-tuning by itself.

Observed:

- `gpt-5.5` mostly passes schema but has semantic mismatches.
- `gpt-5-nano` mostly fails format/schema even after a larger output budget.

Next step before tuning:

- rerun the expanded 32-case hard benchmark;
- run open-source families/weights;
- identify repeated semantic mismatch clusters;
- only then generate supervised fine-tuning data.
