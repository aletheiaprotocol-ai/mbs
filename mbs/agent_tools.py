"""JSON-callable agent tool surface for MBS.

This module is intentionally transport-neutral. It gives agent runtimes,
workflow engines, and MCP-style wrappers a small stable surface that can be
called with plain JSON objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ._version import __version__
from .bench import mock_output
from .check import check
from .compiler import canonical_json, compile_schema, estimate_tokens, load_schema
from .cost import report_cost
from .trace import create_trace
from .validate import validate_output


class AgentToolError(ValueError):
    """Raised when an MBS agent tool request is invalid."""


AGENT_TOOL_CONTRACT_VERSION = "mbs-agent-tools/v1"


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def list_agent_tools() -> list[dict[str, Any]]:
    """Return transport-neutral tool descriptors for agent integrations."""
    return [
        {
            "name": "mbs.compile",
            "description": "Compile a JSON Schema into an MBS behavioral contract.",
            "contract_version": AGENT_TOOL_CONTRACT_VERSION,
            "stability": "stable",
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
            "contract_version": AGENT_TOOL_CONTRACT_VERSION,
            "stability": "stable",
            "input_schema": {
                "type": "object",
                "properties": {
                    "schema": {"type": "object"},
                    "schema_path": {"type": "string"},
                    "output": {"description": "Output object or raw JSON string."},
                    "output_path": {"type": "string", "description": "Path to an output JSON file."},
                },
            },
        },
        {
            "name": "mbs.check",
            "description": "Compile, validate, trace, and return one MBS result.",
            "contract_version": AGENT_TOOL_CONTRACT_VERSION,
            "stability": "stable",
            "input_schema": {
                "type": "object",
                "properties": {
                    "schema": {"type": "object"},
                    "schema_path": {"type": "string"},
                    "input": {"type": "string"},
                    "output": {"description": "Optional output object or raw JSON string."},
                    "output_path": {"type": "string", "description": "Optional path to an output JSON file."},
                    "model": {"type": "string"},
                    "format": {"type": "string", "enum": ["natural", "progressive", "full", "strict"]},
                },
            },
        },
        {
            "name": "mbs.trace",
            "description": "Create a portable MBS trace for a schema/output pair.",
            "contract_version": AGENT_TOOL_CONTRACT_VERSION,
            "stability": "stable",
            "input_schema": {
                "type": "object",
                "properties": {
                    "schema": {"type": "object"},
                    "schema_path": {"type": "string"},
                    "output": {"description": "Output object or raw JSON string."},
                    "output_path": {"type": "string", "description": "Path to an output JSON file."},
                    "input": {"type": "string"},
                    "model": {"type": "string"},
                    "format": {"type": "string", "enum": ["natural", "progressive", "full", "strict"]},
                },
            },
        },
        {
            "name": "mbs.cost",
            "description": "Report cost per valid structured output from result records.",
            "contract_version": AGENT_TOOL_CONTRACT_VERSION,
            "stability": "stable",
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
    return success_envelope(name, call_agent_tool(name, arguments))


def success_envelope(tool: str, result: dict[str, Any]) -> dict[str, Any]:
    """Return the stable v1 agent-tool success envelope."""
    return {
        "ok": True,
        "tool": tool,
        "contract_version": AGENT_TOOL_CONTRACT_VERSION,
        "mbs_version": __version__,
        "result": result,
        "error": None,
    }


def error_envelope(tool: str | None, error: Exception) -> dict[str, Any]:
    """Return the stable v1 agent-tool error envelope without tracebacks."""
    return {
        "ok": False,
        "tool": tool,
        "contract_version": AGENT_TOOL_CONTRACT_VERSION,
        "mbs_version": __version__,
        "result": None,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "retryable": False,
        },
    }


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
    return validate_output(schema, _output_arg(args, required=True))


def _tool_check(args: dict[str, Any]) -> dict[str, Any]:
    schema = _schema_arg(args)
    return check(
        schema,
        input=str(args.get("input", "")),
        output=_output_arg(args, required=False),
        model=str(args.get("model", "agent")),
        format=str(args.get("format", "full")),
    )


def _tool_trace(args: dict[str, Any]) -> dict[str, Any]:
    schema = _schema_arg(args)
    output = _output_arg(args, required=True)
    contract = compile_schema(schema, format=str(args.get("format", "full")))
    validation = validate_output(schema, output)
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
        try:
            schema = load_schema(str(args["schema_path"]))
        except FileNotFoundError as exc:
            raise AgentToolError(f"schema file not found: {args['schema_path']}") from exc
        except json.JSONDecodeError as exc:
            raise AgentToolError(
                f"invalid JSON in schema {args['schema_path']}: line {exc.lineno} column {exc.colno}: {exc.msg}"
            ) from exc
        if not isinstance(schema, dict):
            raise AgentToolError(f"schema must be a JSON object: {args['schema_path']}")
        return schema
    raise AgentToolError("MBS agent tool requires schema or schema_path")


def _output_arg(args: dict[str, Any], *, required: bool) -> Any:
    if "output" in args:
        return args["output"]
    if "output_path" in args:
        p = Path(str(args["output_path"]))
        if not p.exists():
            raise AgentToolError(f"output file not found: {p}")
        try:
            return json.loads(p.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise AgentToolError(f"invalid JSON in output {p}: line {exc.lineno} column {exc.colno}: {exc.msg}") from exc
    if required:
        raise AgentToolError("MBS agent tool requires output or output_path")
    return None


def mock_agent_output(schema: dict[str, Any], input_text: str = "") -> dict[str, Any]:
    """Expose the deterministic local mock for demos and agent tests."""
    return mock_output(schema, input_text)