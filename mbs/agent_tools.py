"""JSON-callable agent tool surface for MBS.

This module is intentionally transport-neutral. It gives agent runtimes,
workflow engines, and MCP-style wrappers a small stable surface that can be
called with plain JSON objects.
"""

from __future__ import annotations

from typing import Any, Callable

from .bench import mock_output
from .check import check
from .compiler import canonical_json, compile_schema, estimate_tokens, load_schema
from .cost import report_cost
from .trace import create_trace
from .validate import validate_output


class AgentToolError(ValueError):
    """Raised when an MBS agent tool request is invalid."""


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def list_agent_tools() -> list[dict[str, Any]]:
    """Return transport-neutral tool descriptors for agent integrations."""
    return [
        {
            "name": "mbs.compile",
            "description": "Compile a JSON Schema into an MBS behavioral contract.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "schema": {"type": "object", "description": "JSON Schema object."},
                    "schema_path": {"type": "string", "description": "Path to a JSON Schema file."},
                    "format": {"type": "string", "enum": ["natural", "progressive", "full", "strict"]},
                    "task_context": {"type": "string"},
                    "include_free_enums": {"type": "boolean"},
                },
            },
        },
        {
            "name": "mbs.validate",
            "description": "Validate a structured output against a JSON Schema.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "schema": {"type": "object"},
                    "schema_path": {"type": "string"},
                    "output": {"description": "Output object or raw JSON string."},
                },
                "required": ["output"],
            },
        },
        {
            "name": "mbs.check",
            "description": "Compile, validate, trace, and return one MBS result.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "schema": {"type": "object"},
                    "schema_path": {"type": "string"},
                    "input": {"type": "string"},
                    "output": {"description": "Optional output object or raw JSON string."},
                    "model": {"type": "string"},
                    "format": {"type": "string", "enum": ["natural", "progressive", "full", "strict"]},
                },
            },
        },
        {
            "name": "mbs.trace",
            "description": "Create a portable MBS trace for a schema/output pair.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "schema": {"type": "object"},
                    "schema_path": {"type": "string"},
                    "output": {"description": "Output object or raw JSON string."},
                    "input": {"type": "string"},
                    "model": {"type": "string"},
                    "format": {"type": "string", "enum": ["natural", "progressive", "full", "strict"]},
                },
                "required": ["output"],
            },
        },
        {
            "name": "mbs.cost",
            "description": "Report cost per valid structured output from result records.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "records": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["records"],
            },
        },
    ]


def call_agent_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call an MBS agent tool by name using JSON-compatible arguments."""
    args = arguments or {}
    handlers: dict[str, ToolHandler] = {
        "mbs.compile": _tool_compile,
        "mbs.validate": _tool_validate,
        "mbs.check": _tool_check,
        "mbs.trace": _tool_trace,
        "mbs.cost": _tool_cost,
    }
    try:
        handler = handlers[name]
    except KeyError as exc:
        available = ", ".join(sorted(handlers))
        raise AgentToolError(f"Unknown MBS agent tool: {name}. Available tools: {available}") from exc
    return handler(args)


def handle_agent_tool_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle a generic JSON request with tool/name and arguments keys."""
    if not isinstance(request, dict):
        raise AgentToolError("Agent tool request must be a JSON object")
    name = request.get("tool") or request.get("name")
    if not isinstance(name, str) or not name:
        raise AgentToolError("Agent tool request requires a string tool/name")
    arguments = request.get("arguments", {})
    if not isinstance(arguments, dict):
        raise AgentToolError("Agent tool request arguments must be a JSON object")
    return {"tool": name, "result": call_agent_tool(name, arguments)}


def _tool_compile(args: dict[str, Any]) -> dict[str, Any]:
    schema = _schema_arg(args)
    return compile_schema(
        schema,
        format=str(args.get("format", "full")),
        task_context=str(args.get("task_context", "")),
        include_free_enums=bool(args.get("include_free_enums", False)),
    )


def _tool_validate(args: dict[str, Any]) -> dict[str, Any]:
    schema = _schema_arg(args)
    if "output" not in args:
        raise AgentToolError("mbs.validate requires output")
    return validate_output(schema, args["output"])


def _tool_check(args: dict[str, Any]) -> dict[str, Any]:
    schema = _schema_arg(args)
    return check(
        schema,
        input=str(args.get("input", "")),
        output=args.get("output", None),
        model=str(args.get("model", "agent")),
        format=str(args.get("format", "full")),
    )


def _tool_trace(args: dict[str, Any]) -> dict[str, Any]:
    schema = _schema_arg(args)
    if "output" not in args:
        raise AgentToolError("mbs.trace requires output")
    contract = compile_schema(schema, format=str(args.get("format", "full")))
    validation = validate_output(schema, args["output"])
    output_tokens = estimate_tokens(canonical_json(validation.get("output")))
    return create_trace(
        schema,
        contract,
        validation,
        input_text=str(args.get("input", "")),
        model=str(args.get("model", "agent")),
        output_tokens=output_tokens,
    )


def _tool_cost(args: dict[str, Any]) -> dict[str, Any]:
    records = args.get("records")
    if not isinstance(records, list):
        raise AgentToolError("mbs.cost requires records as a list")
    return report_cost(records)


def _schema_arg(args: dict[str, Any]) -> dict[str, Any]:
    if "schema" in args:
        schema = args["schema"]
        if not isinstance(schema, dict):
            raise AgentToolError("schema must be a JSON object")
        return schema
    if "schema_path" in args:
        return load_schema(str(args["schema_path"]))
    raise AgentToolError("MBS agent tool requires schema or schema_path")


def mock_agent_output(schema: dict[str, Any], input_text: str = "") -> dict[str, Any]:
    """Expose the deterministic local mock for demos and agent tests."""
    return mock_output(schema, input_text)