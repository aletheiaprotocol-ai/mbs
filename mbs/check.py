"""High-level MBS check API."""

from __future__ import annotations

from typing import Any

from .bench import mock_output
from .compiler import canonical_json, compile_schema, estimate_tokens, load_schema
from .trace import create_trace
from .validate import validate_output


def check(
    schema: dict[str, Any] | type[Any],
    input: str = "",
    output: str | dict[str, Any] | None = None,
    model: str = "mock",
    format: str = "full",
) -> dict[str, Any]:
    """Compile, validate, trace, and return a single structured result."""
    schema_dict = load_schema(schema) if not isinstance(schema, dict) else schema
    contract = compile_schema(schema_dict, format=format)
    produced = output if output is not None else mock_output(schema_dict, input)
    validation = validate_output(schema_dict, produced)
    output_tokens = estimate_tokens(canonical_json(validation.get("output")))
    trace = create_trace(schema_dict, contract, validation, input_text=input, model=model, output_tokens=output_tokens)
    return {
        "status": validation["status"],
        "failure_reason": validation.get("failure_reason"),
        "trace_id": trace["trace_id"],
        "schema_hash": trace["schema_hash"],
        "contract_hash": trace["contract_hash"],
        "output": validation["output"],
        "validation": validation,
        "trace": trace,
        "contract": contract,
    }
