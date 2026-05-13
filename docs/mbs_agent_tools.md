# MBS Agent Tools

MBS exposes a transport-neutral agent-tools layer for runtimes that need JSON-callable structured-output checks.

The layer is not tied to any server protocol. A wrapper can call it from an agent loop, workflow engine, or MCP-style server.

For native provider JSON-mode and tool-calling evaluation, see
`docs/mbs_json_mode_tool_calling_plan.md`.

## Available Tools

```bash
mbs agent-tools --list
```

Tools:

- `mbs.compile` — compile a JSON Schema into a behavioral contract
- `mbs.validate` — validate structured output against a schema
- `mbs.check` — compile, validate, trace, and return one result
- `mbs.trace` — create a portable trace for a schema/output pair
- `mbs.cost` — compute cost per valid structured output

## SDK Usage

```python
from mbs import call_agent_tool

result = call_agent_tool(
    "mbs.check",
    {
        "schema_path": "examples/fintech_transaction_risk/schema.json",
        "input": "Customer transfers 4800 EUR to a new beneficiary",
        "model": "agent-runtime",
    },
)

assert result["status"] in {"PASS", "REVIEW", "FAIL"}
assert result["trace"]["trace_id"].startswith("mbs_trace_")
```

## Generic Request Shape

Wrappers can use a single JSON request shape:

```json
{
  "tool": "mbs.validate",
  "arguments": {
    "schema_path": "examples/fintech_transaction_risk/schema.json",
    "output": {"decision": "REVIEW", "risk_level": "HIGH", "reason": "new beneficiary"}
  }
}
```

Python:

```python
from mbs import handle_agent_tool_request

response = handle_agent_tool_request(request)
```

CLI:

```bash
mbs agent-tools --request request.json --json
```

## Why This Exists

Agents need a small safety boundary before they call tools, write database rows, or trigger workflows. The MBS agent-tools layer lets an agent ask:

1. What contract should the model follow?
2. Did the output satisfy the schema?
3. What exact failure happened?
4. Is there a trace id for audit and regression testing?
5. What was the cost per valid structured output?

Keep real model execution outside this layer. MBS measures and guards structured behavior around the model output.