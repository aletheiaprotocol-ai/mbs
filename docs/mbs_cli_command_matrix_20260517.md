# MBS CLI Command Matrix Evidence — May 17, 2026

## Scope

This artifact closes the local command-matrix evidence gap for the public `mbs` CLI surface. It is local regression evidence, not remote GitHub Actions evidence.

## Public subcommand inventory

The following public subcommands were verified for `--help` exit `0` and no stderr:

| Subcommand | Help status | Success-path evidence | Controlled failure evidence |
| --- | --- | --- | --- |
| `compile` | PASS | `tests/test_mbs_product.py` compile/contract tests | Missing schema returns `MBS input error: schema file not found` |
| `validate` | PASS | BOM and inline/file output validation tests | Invalid inline/file JSON returns machine-readable invalid JSON or controlled input error |
| `check` | PASS | `check` with trace output creates parent directories | Missing output file returns controlled input error |
| `trace` | PASS | Direct trace output creates parent directories | Missing output file returns controlled input error |
| `cost` | PASS | Cost report tests over records | Missing records, malformed JSONL, and non-object records return controlled input errors |
| `bench` | PASS | Config and schema/case benchmark tests | Missing cases/config mistakes return controlled input errors |
| `demo` | PASS | CI workflow runs deterministic demo artifact generation | Help and demo paths covered by full suite |
| `test` | PASS | Structured-output regression test matrix | Missing schema directory returns controlled input error |
| `lang` | PASS | Language contract/BOM matrix tests | Missing schema returns controlled input error |
| `report` | PASS | Empty and populated report tests | Empty/missing result patterns return nonzero JSON report without traceback |
| `gate` | PASS | Passing/failing threshold gate tests | Bad config object returns controlled input error |
| `evidence-pack` | PASS | Fixture/CI evidence pack tests | Empty result rows return controlled input error |
| `compare` | PASS | Regression and no-match comparison tests | No-match returns nonzero JSON payload without traceback |
| `retry-audit` | PASS | Retry matrix/audit tests | Empty/missing retry rows return controlled input error |
| `models` | PASS | Model registry suite tests | Unknown suite returns controlled input error |
| `triage` | PASS | Remote/fixture triage tests | Missing result rows return controlled input error |
| `agent-tools` | PASS | Agent tool request/call tests | Unknown tool and bad argument envelopes return controlled input errors |
| `adapt-responses` | PASS | Provider-response fixture adaptation tests | Missing response file returns controlled input error |
| `make-response-template` | PASS | Template generation tests | Missing cases file returns controlled input error |

## Help transcript summary

PowerShell-safe verification command used locally:

```text
python -c "from mbs.cli import main; import io, contextlib; commands=[...]; ... main([cmd,'--help']) ..."
```

Observed summary:

```text
compile|exit=0|stdout=20|stderr=0
validate|exit=0|stdout=7|stderr=0
check|exit=0|stdout=12|stderr=0
trace|exit=0|stdout=10|stderr=0
cost|exit=0|stdout=9|stderr=0
bench|exit=0|stdout=11|stderr=0
demo|exit=0|stdout=6|stderr=0
test|exit=0|stdout=12|stderr=0
lang|exit=0|stdout=14|stderr=0
report|exit=0|stdout=13|stderr=0
gate|exit=0|stdout=12|stderr=0
evidence-pack|exit=0|stdout=21|stderr=0
compare|exit=0|stdout=16|stderr=0
retry-audit|exit=0|stdout=10|stderr=0
models|exit=0|stdout=13|stderr=0
triage|exit=0|stdout=20|stderr=0
agent-tools|exit=0|stdout=10|stderr=0
adapt-responses|exit=0|stdout=24|stderr=0
make-response-template|exit=0|stdout=13|stderr=0
```

## Regression anchors

- `tests/test_mbs_product.py::test_cli_routine_misuse_returns_controlled_errors`
- `tests/test_mbs_product.py::test_cli_edge_command_matrix_returns_controlled_errors`
- `tests/test_mbs_product.py::test_cli_artifact_commands_accept_bom_encoded_inputs`
- `tests/test_mbs_conformance.py::test_cli_validate_malformed_inline_json_emits_machine_readable_failure`
- `tests/test_ci_release_workflow.py`

## Closure statement

Local command-matrix evidence is complete for the public subcommands listed above. Remote non-Windows CI evidence remains a separate blocker tracked as B-001/B-009.
