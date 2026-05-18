# MBS Agent Tool Contract v1

## Status

`mbs-agent-tools/v1` is the stable local contract for transport-neutral agent integrations. It is a software/API contract, not provider benchmark evidence.

## Tools

The stable tool names are:

- `mbs.compile`
- `mbs.validate`
- `mbs.check`
- `mbs.trace`
- `mbs.cost`

Every descriptor returned by `mbs agent-tools --list --json` includes:

- `name`
- `description`
- `contract_version: "mbs-agent-tools/v1"`
- `stability: "stable"`
- `input_schema`

## Success envelope

JSON CLI calls through `mbs agent-tools --call ... --json` and `mbs agent-tools --request ... --json` return:

- `ok: true`
- `tool`
- `contract_version`
- `mbs_version`
- `result`
- `error: null`

## Error envelope

Controlled agent-tool input failures return exit code `2` and:

- `ok: false`
- `tool`
- `contract_version`
- `mbs_version`
- `result: null`
- `error.type`
- `error.message`
- `error.retryable: false`

The error envelope must not include Python tracebacks for ordinary input errors such as unknown tool names, missing files, non-object request payloads, or invalid tool arguments.

## Trace fields

`mbs.check` and `mbs.trace` results include trace evidence with:

- `trace_id`
- `schema_hash`
- `contract_hash`
- `input_hash`
- `output_hash`
- `model`
- `mbs_version`
- `validator_version`
- `timestamp`
- `status`
- `errors`
- `tokens`

## Path inputs

`schema_path`, `output_path`, and request/config JSON files are decoded with UTF-8 BOM tolerance where applicable.

## Boundary

This contract stabilizes local agent integration behavior. It does not certify semantic safety, provider reliability, hosted availability, or Enterprise Pilot readiness without separate CI, provider, and governance evidence.