# Regression Enum Failure Demo

This example shows why MBS is structured-output testing, not only prompt compression.

Run:

```bash
mbs bench \
  --schema examples/regression_enum_failure/schema.json \
  --cases examples/regression_enum_failure/cases.jsonl \
  --out benchmarks/results/regression_enum_failure.json

mbs report --results benchmarks/results/regression_enum_failure.json
```

Expected failure types:

- `invented_enum` when a model invents `unlock_account`.
- `missing_required_key` when the required `reason` field is absent.
- one control case that passes.
