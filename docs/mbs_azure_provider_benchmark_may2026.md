# MBS Azure Provider Structured-Output Benchmark — May 2026

This report records a real provider-mode MBS benchmark run against Azure OpenAI deployments. It is evidence for these exact deployments, schema, cases, modes, and run settings only.

## Scope

Schema: `examples/hard_agent_routing/schema.json`

Cases: `examples/hard_agent_routing/cases.jsonl`

Models/deployments tested:

- `gpt-5.5`
- `gpt-5-nano`

Modes tested:

- text
- JSON mode
- tool calling

Rows:

- 6 hard cases per model/mode
- 36 total provider calls in the final larger-budget comparison
- 0 infrastructure failures
- 36 traceable rows
- The fixture has since been expanded to 32 cases for the next evidence gate.

## Why This Is Hard Enough To Fail

The cases require more than valid JSON. They require correct routing across:

- action enum;
- priority enum;
- human escalation decision;
- customer-visible flag;
- risk tags;
- rationale.

The test produced both format failures and semantic mismatches, so it is not a trivial smoke test.

## Summary Result

Final larger-budget comparison:

| model | schema valid | semantic correct | clean JSON | top failures |
| --- | ---: | ---: | ---: | --- |
| `gpt-5.5` | 0.9444 | 0.5000 | 0.9444 | `semantic_mismatch:8`, `invalid_json:1` |
| `gpt-5-nano` | 0.1667 | 0.0556 | 0.1667 | `invalid_json:15`, `semantic_mismatch:2` |

Overall:

- mean schema-valid rate: 0.5555
- mean semantic-correct rate: 0.2778
- mean clean-JSON rate: 0.5555

## Expanded Tool-Call Gate

After the first report, the hard fixture was expanded to 32 cases and rerun in
tool-call mode.

| model | cases | infra failures | schema valid | semantic correct | clean JSON | top failures |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `gpt-5.5` | 32 | 0 | 1.0000 | 0.2500 | 1.0000 | `semantic_mismatch:24` |
| `gpt-5-nano` | 32 | 0 | 0.0625 | 0.0000 | 0.0625 | `invalid_json:30`, `semantic_mismatch:2` |

An initial expanded `gpt-5.5` run against the wrong Azure endpoint produced
`DeploymentNotFound` for all 32 rows. MBS correctly classified those rows as
infrastructure failures and they were excluded from model-behavior evidence.
The rerun used the correct Sweden endpoint/key environment for `gpt-5.5`.

The expanded gate is stronger evidence than the six-case bridge run because it
shows repeated semantic mismatches across a larger reviewed case set while
keeping infrastructure failures separate.

## Interpretation

`gpt-5.5` mostly produced valid structured JSON but still failed on semantic routing decisions. This is exactly the kind of failure MBS is designed to expose beyond JSON validation.

`gpt-5-nano` failed mostly at the format level. Increasing max completion tokens from 256 to 768 improved it from 0 schema-valid rows to a small number of valid rows, but did not make it reliable on this hard routing task.

Tool calling improved schema validity for `gpt-5.5` versus text mode but did not
solve semantic correctness. This is a warning against assuming tool calling
alone improves real task correctness.

## What This Proves

- MBS can run real provider-mode structured-output tests.
- MBS separates infrastructure failures from model behavior failures.
- MBS catches both format failures and semantic failures.
- Valid JSON/schema compliance is not enough to establish agent reliability.

## What This Does Not Prove

- It does not prove universal provider quality.
- It does not prove `gpt-5.5` is always better than `gpt-5-nano`.
- It does not prove tool calling is worse in general.
- It does not prove fine-tuning is required yet.

## Next Evidence Gate

The next gate is to run the same schema and cases against open-source model families and weights:

- Qwen 3B / 14B / 72B-AWQ
- Llama 8B / 70B-AWQ
- Mixtral 8x7B / AWQ

Then compare failures by family, size, and decoding mode.

Before making headline claims, run OSS providers on the expanded 32-case fixture
and compare per-case semantic mismatches by family, weight, and decoding mode.
