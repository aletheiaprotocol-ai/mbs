# Agent Workflow: Transaction Review

This is an agent-first workflow proof for MBS. It shows how an agent can validate a structured fintech transaction decision before taking action.

## Goal

An agent receives a transaction event and must decide whether it can continue, needs step-up authentication, must be held for review, or must be blocked. MBS acts as the machine-readable contract gate.

## Files

- `input_event.json` — transaction event given to the agent.
- `schema.json` — strict output contract copied from the fintech workflow pack.
- `candidate_good.json` — schema-valid model/tool output.
- `candidate_bad.json` — invalid output with missing keys and invented enums.
- `agent_tool_request_good.json` — JSON-callable MBS agent tool request.
- `agent_tool_request_bad.json` — failing MBS agent tool request.
- `run_workflow.ps1` — replayable Windows demo that validates both outputs and writes traces.

## Exact commands

From the repo root:

```powershell
python -m mbs.cli validate --schema examples/agent_workflow_transaction_review/schema.json --output examples/agent_workflow_transaction_review/candidate_good.json --json
python -m mbs.cli validate --schema examples/agent_workflow_transaction_review/schema.json --output examples/agent_workflow_transaction_review/candidate_bad.json --json
python -m mbs.cli check --schema examples/agent_workflow_transaction_review/schema.json --input (Get-Content -Raw examples/agent_workflow_transaction_review/input_event.json) --output examples/agent_workflow_transaction_review/candidate_good.json --model transaction-review-agent --trace-out examples/agent_workflow_transaction_review/trace_good.json --json
python -m mbs.cli agent-tools --request examples/agent_workflow_transaction_review/agent_tool_request_good.json --json
```

Or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File examples/agent_workflow_transaction_review/run_workflow.ps1
```

## Agent decision policy

- `PASS` + `decision=APPROVE` or `STEP_UP_AUTH`: continue with the specified control.
- `PASS` + `decision=HOLD_REVIEW` or `BLOCK`: do not execute payment; create audit ticket.
- `FAIL`: retry with the MBS failure reason if safe, otherwise route to human review.
- `REVIEW`: route to human review because the output is schema-valid but has warnings.

## Expected behavior

- `candidate_good.json` returns `PASS` and creates a trace ID.
- `candidate_bad.json` returns `FAIL`, with failure reasons including missing required keys and invented enum values.
- The trace file contains schema hash, contract hash, input hash, output hash, status, failure reason, errors, and token accounting.
