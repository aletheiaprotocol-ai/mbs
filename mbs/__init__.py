"""MBS: Minimal Behavioral Specification for structured agent outputs."""

from .agent_tools import call_agent_tool, handle_agent_tool_request, list_agent_tools, mock_agent_output
from .adapter import adapt_response_jsonl, make_response_template, write_response_template
from .compiler import (
    classify_enum,
    compile_schema,
    extract_fields,
    format_report,
    load_schema,
)
from .check import check
from .compare import compare_results, format_compare
from .cost import report_cost
from .models import load_model_registry, suite_models, suite_summary, validate_suite_coverage
from .report import aggregate_results, dimension_scorecards, failure_summary, markdown_report, model_scorecards, trace_errors
from .retry import build_retry_prompt, retry_guidance
from .retry_audit import audit_retry_attempts
from .trace import create_trace
from .triage import format_triage, triage_results
from .validate import validate_output

__all__ = [
    "aggregate_results",
    "adapt_response_jsonl",
    "audit_retry_attempts",
    "build_retry_prompt",
    "call_agent_tool",
    "classify_enum",
    "check",
    "compare_results",
    "compile_schema",
    "create_trace",
    "dimension_scorecards",
    "extract_fields",
    "format_compare",
    "format_report",
    "format_triage",
    "failure_summary",
    "handle_agent_tool_request",
    "list_agent_tools",
    "load_model_registry",
    "load_schema",
    "markdown_report",
    "make_response_template",
    "mock_agent_output",
    "model_scorecards",
    "report_cost",
    "retry_guidance",
    "suite_models",
    "suite_summary",
    "triage_results",
    "trace_errors",
    "validate_suite_coverage",
    "validate_output",
    "write_response_template",
]
