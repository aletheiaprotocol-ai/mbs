# MBS v0.1.1 Release Notes

Planned release date: May 2026.

## Summary

MBS v0.1.1 focuses on structured-output adapter usability and evidence discipline. It adds a provider-response JSONL path, smoke fixtures, a template generator, and buyer-facing triage documentation.

## Added

- `mbs adapt-responses`: converts provider-response JSONL into normal MBS benchmark result JSON.
- `mbs make-response-template`: creates provider-response JSONL templates from benchmark cases.
- Support for common provider output fields:
  - `output`
  - `response`
  - `content`
  - `arguments`
  - `tool_arguments`
  - `tool_call.arguments`
  - `tool_call.function.arguments`
  - first item in `tool_calls`
- Optional `--cases` merge for `adapt-responses`, matching by `case_id` / `id`, then row order.
- Public adapter smoke fixtures under `examples/tool_argument_generation/`.
- Failure triage guide: `docs/mbs_failure_triage_examples.md`.

## Changed

- Adapter documentation now includes a reproducible `adapt-responses → report → compare` smoke pipeline.
- README includes the adapter command and fixture pointers.

## Validation

Current validation before release:

- Full test suite passes locally.
- Package build succeeds.
- Adapter smoke pipeline validates fixture conversion, trace coverage, report aggregation, and comparison.

## Evidence Limits

The included provider fixtures are smoke tests. They prove MBS plumbing works. They do not prove provider/model reliability.

Benchmark evidence still requires:

- real provider/model outputs;
- hard enough cases to fail;
- multiple schemas;
- trace coverage;
- separated infrastructure failures;
- compare reports;
- retry audits when retry is enabled.

## Upgrade Notes

No breaking API changes are expected from v0.1.0.
