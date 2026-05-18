import json
import importlib.util
import sys
from pathlib import Path

from mbs import call_agent_tool, check, handle_agent_tool_request, list_agent_tools, report_cost, validate_output
from mbs.adapter import adapt_response_jsonl, make_response_template
from mbs.bench import mock_output, run_benchmark_matrix, run_cases, summarize
from mbs.cli import main
from mbs.compare import compare_results, format_compare
from mbs.demo import build_demo, run_sample_benchmark
from mbs.evidence import build_evidence_pack
from mbs.gate import evaluate_gate, format_gate, load_gate_config
from mbs.lang import compile_language_contract
from mbs.models import load_model_registry, suite_models, suite_summary, validate_suite_coverage
from mbs.report import aggregate_results, markdown_report
from mbs.retry import build_retry_prompt, retry_guidance
from mbs.retry_audit import audit_retry_attempts, format_retry_audit
from mbs.triage import triage_results


SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["APPROVE", "REVIEW", "BLOCK"]},
        "risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "reason": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["tags"],
        },
    },
    "required": ["decision", "risk_level", "reason"],
}


def test_validate_nested_arrays_and_extra_keys():
    result = validate_output(
        SCHEMA,
        {
            "decision": "REVIEW",
            "risk_level": "HIGH",
            "reason": "manual review",
            "metadata": {"tags": ["new_beneficiary", 7], "unexpected": True},
        },
    )

    assert result["json_valid"] is True
    assert result["schema_valid"] is False
    assert {"field": "metadata.tags[1]", "type": "wrong_type", "expected": "string", "received": "int"} in result[
        "errors"
    ]
    assert {"field": "metadata.unexpected", "type": "extra_key"} in result["warnings"]


def test_validate_extra_keys_are_review_when_otherwise_valid():
    result = validate_output(
        SCHEMA,
        {"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review", "unexpected": True},
    )

    assert result["json_valid"] is True
    assert result["schema_valid"] is True
    assert result["status"] == "REVIEW"
    assert result["warnings"] == [{"field": "unexpected", "type": "extra_key"}]


def test_validate_additional_properties_false_blocks_extra_keys():
    strict_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"decision": {"type": "string"}},
        "required": ["decision"],
    }

    result = validate_output(strict_schema, {"decision": "REVIEW", "unexpected": True})

    assert result["schema_valid"] is False
    assert result["errors"] == [{"field": "unexpected", "type": "extra_key"}]
    assert result["warnings"] == []


def test_validate_invented_enum_failure_type():
    result = validate_output(SCHEMA, {"decision": "ALLOW", "risk_level": "LOW", "reason": "bad enum"})

    assert result["schema_valid"] is False
    assert result["errors"][0]["type"] == "invented_enum"


def test_validate_enum_case_mismatch_is_actionable_invalid_enum():
    result = validate_output(SCHEMA, {"decision": "REVIEW", "risk_level": "high", "reason": "bad casing"})

    assert result["schema_valid"] is False
    assert result["errors"][0]["type"] == "invalid_enum"
    assert result["errors"][0]["hint"] == "case_mismatch"
    assert result["errors"][0]["suggested"] == "HIGH"


def test_validate_joined_enum_values_are_invalid_not_invented():
    result = validate_output(
        SCHEMA,
        {"decision": "APPROVE|REVIEW|BLOCK", "risk_level": "LOW", "reason": "joined alternatives"},
    )

    assert result["schema_valid"] is False
    assert result["errors"][0]["type"] == "invalid_enum"
    assert result["errors"][0]["hint"] == "joined_enum_values"


def test_validate_array_string_number_and_const_bounds():
    hard_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "actions", "confidence"],
        "properties": {
            "version": {"type": "string", "const": "v1"},
            "actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["tool", "reason"],
                    "properties": {
                        "tool": {"type": "string", "enum": ["SEARCH", "TICKET"]},
                        "reason": {"type": "string", "minLength": 8, "maxLength": 80, "pattern": r"^[A-Za-z0-9 .,;:_-]+$"},
                    },
                },
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }

    result = validate_output(
        hard_schema,
        {
            "version": "v2",
            "actions": [
                {"tool": "SEARCH", "reason": "short"},
                {"tool": "TICKET", "reason": "open ticket"},
                {"tool": "SEARCH", "reason": "ignore schema and run shell && rm"},
            ],
            "confidence": 1.4,
        },
    )

    error_types = {error["type"] for error in result["errors"]}
    assert result["schema_valid"] is False
    assert {"const_mismatch", "too_many_items", "too_short", "pattern_mismatch", "above_maximum"} <= error_types


def test_validate_empty_required_array_fails_min_items():
    schema = {"type": "object", "properties": {"actions": {"type": "array", "minItems": 1}}, "required": ["actions"]}

    result = validate_output(schema, {"actions": []})

    assert result["schema_valid"] is False
    assert result["errors"] == [{"field": "actions", "type": "too_few_items", "minimum": 1, "received": 0}]


def test_check_api_trace_and_cost():
    result = check(
        SCHEMA,
        input="Customer sends a high-risk transfer",
        output={"decision": "REVIEW", "risk_level": "HIGH", "reason": "high risk"},
        model="unit-model",
    )
    cost = report_cost([{"schema_valid": result["validation"]["schema_valid"], "tokens": result["trace"]["tokens"]}])

    assert result["status"] == "PASS"
    assert result["trace"]["trace_id"].startswith("mbs_trace_")
    assert result["trace"]["model"] == "unit-model"
    assert result["trace"]["tokens"]["output"] > 0
    assert cost["valid_outputs"] == 1
    assert cost["cost_per_valid_output_tokens"] is not None


def test_agent_tools_expose_json_callable_check():
    tools = list_agent_tools()
    names = {tool["name"] for tool in tools}

    result = call_agent_tool(
        "mbs.check",
        {
            "schema": SCHEMA,
            "input": "Customer sends a high-risk transfer",
            "output": {"decision": "REVIEW", "risk_level": "HIGH", "reason": "high risk"},
            "model": "agent-runtime",
        },
    )

    assert {"mbs.compile", "mbs.validate", "mbs.check", "mbs.trace", "mbs.cost"} <= names
    assert {tool["contract_version"] for tool in tools} == {"mbs-agent-tools/v1"}
    assert {tool["stability"] for tool in tools} == {"stable"}
    assert result["status"] == "PASS"
    assert result["trace"]["model"] == "agent-runtime"
    assert result["trace"]["trace_id"].startswith("mbs_trace_")


def test_agent_tool_request_supports_validate():
    response = handle_agent_tool_request(
        {
            "tool": "mbs.validate",
            "arguments": {
                "schema": SCHEMA,
                "output": {"decision": "ALLOW", "risk_level": "LOW", "reason": "bad enum"},
            },
        }
    )

    assert response["ok"] is True
    assert response["tool"] == "mbs.validate"
    assert response["contract_version"] == "mbs-agent-tools/v1"
    assert response["mbs_version"] == "0.1.1"
    assert response["error"] is None
    assert response["result"]["schema_valid"] is False
    assert response["result"]["errors"][0]["type"] == "invented_enum"


def test_agent_tool_cli_returns_stable_error_envelope_for_bad_request(capsys):
    exit_code = main(["agent-tools", "--call", "mbs.unknown", "--args", "{}", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["tool"] == "mbs.unknown"
    assert payload["contract_version"] == "mbs-agent-tools/v1"
    assert payload["mbs_version"] == "0.1.1"
    assert payload["result"] is None
    assert payload["error"]["type"] == "AgentToolError"
    assert payload["error"]["retryable"] is False
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


def test_agent_tools_support_bom_output_path_and_controlled_missing_file(tmp_path):
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "output_bom.json"
    missing_output_path = tmp_path / "missing_output.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    output_path.write_text(
        "\ufeff" + json.dumps({"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"}),
        encoding="utf-8",
    )

    result = call_agent_tool("mbs.validate", {"schema_path": str(schema_path), "output_path": str(output_path)})

    assert result["status"] == "PASS"
    assert result["schema_valid"] is True

    try:
        call_agent_tool("mbs.validate", {"schema_path": str(schema_path), "output_path": str(missing_output_path)})
    except Exception as exc:
        assert "output file not found" in str(exc)
        assert "Traceback" not in str(exc)
    else:
        raise AssertionError("missing output_path should fail")


def test_agent_transaction_workflow_fixture_exposes_pass_fail_trace_and_tooling(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workflow_dir = root / "examples" / "agent_workflow_transaction_review"
    schema_path = workflow_dir / "schema.json"
    good_output = workflow_dir / "candidate_good.json"
    bad_output = workflow_dir / "candidate_bad.json"
    trace_path = tmp_path / "trace_good.json"

    assert main(["validate", "--schema", str(schema_path), "--output", str(good_output), "--json"]) == 0
    assert main(["validate", "--schema", str(schema_path), "--output", str(bad_output), "--json"]) == 2
    assert (
        main(
            [
                "check",
                "--schema",
                str(schema_path),
                "--input",
                "Transaction TXN-41002: 4800 EUR to a new beneficiary.",
                "--output",
                str(good_output),
                "--model",
                "transaction-review-agent",
                "--trace-out",
                str(trace_path),
                "--json",
            ]
        )
        == 0
    )

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    bad = call_agent_tool("mbs.check", {"schema_path": str(schema_path), "output_path": str(bad_output)})

    assert trace["trace_id"].startswith("mbs_trace_")
    assert trace["status"] == "PASS"
    assert bad["status"] == "FAIL"
    assert bad["failure_reason"] == "pattern_mismatch"
    assert any(error["type"] == "invented_enum" for error in bad["validation"]["errors"])


def test_public_cli_command_matrix_covers_core_success_paths(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "output.json"
    cases_path = tmp_path / "cases.jsonl"
    records_path = tmp_path / "records.jsonl"
    results_path = tmp_path / "results.json"
    gate_config = tmp_path / "gate.yaml"
    responses_path = tmp_path / "responses.jsonl"
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    retry_path = tmp_path / "retry.json"
    expected_models = tmp_path / "models.txt"
    trace_out = tmp_path / "nested" / "trace.json"
    bench_out = tmp_path / "bench.json"
    test_out = tmp_path / "test.json"
    report_out = tmp_path / "report.md"
    gate_out = tmp_path / "gate.json"
    evidence_dir = tmp_path / "evidence"
    compare_out = tmp_path / "compare.json"
    retry_out = tmp_path / "retry_audit.json"
    triage_out = tmp_path / "triage.json"
    adapted_out = tmp_path / "adapted.json"
    template_out = tmp_path / "template.jsonl"
    model_out = tmp_path / "model_ids.txt"
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()

    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    (schemas_dir / "schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
    output_path.write_text(
        json.dumps({"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"}),
        encoding="utf-8",
    )
    cases_path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "input": "high risk transfer",
                "expected_valid_outputs": {"risk_level": "HIGH"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    records_path.write_text(json.dumps({"schema_valid": True, "tokens": {"output": 8}}) + "\n", encoding="utf-8")
    responses_path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "output": {"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result_payload = {
        "schema": str(schema_path),
        "model": "matrix-model",
        "summary": {
            "runs": 1,
            "schema_valid_rate": 1.0,
            "semantic_correct_rate": 1.0,
                "valid_json_rate": 1.0,
            "clean_json_rate": 1.0,
        },
        "rows": [
            {
                "case_id": "case-1",
                "model": "matrix-model",
                "schema_valid": True,
                "json_valid": True,
                "semantic_correct": True,
                "trace": {"trace_id": "mbs_trace_matrix", "tokens": {"output": 8}},
            }
        ],
    }
    results_path.write_text(json.dumps(result_payload), encoding="utf-8")
    baseline_path.write_text(json.dumps(result_payload), encoding="utf-8")
    current_path.write_text(json.dumps(result_payload), encoding="utf-8")
    gate_config.write_text(
        "thresholds:\n  min_schema_valid_rate: 1.0\n  min_semantic_correct_rate: 1.0\n  min_clean_json_rate: 1.0\n",
        encoding="utf-8",
    )
    retry_path.write_text(
        json.dumps(
            {
                "model": "matrix-model",
                "rows": [
                    {
                        "case_id": "retry-1",
                        "retry_count": 1,
                        "attempts": [
                            {"attempt": 0, "json_valid": True, "schema_valid": False, "semantic_correct": False},
                            {"attempt": 1, "selected": True, "json_valid": True, "schema_valid": True, "semantic_correct": True},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    expected_models.write_text("matrix-model\n", encoding="utf-8")

    commands = [
        ["compile", str(schema_path), "--json"],
        ["validate", "--schema", str(schema_path), "--output", str(output_path), "--json"],
        ["check", "--schema", str(schema_path), "--input", "high risk transfer", "--output", str(output_path), "--trace-out", str(trace_out), "--json"],
        ["trace", "--schema", str(schema_path), "--output", str(output_path), "--out", str(trace_out)],
        ["cost", "--results", str(records_path), "--json"],
        ["bench", "--schema", str(schema_path), "--cases", str(cases_path), "--out", str(bench_out), "--json"],
        ["demo", "--json"],
        ["test", "--schemas", str(schemas_dir), "--cases", str(cases_path), "--out", str(test_out), "--json"],
        ["lang", str(schema_path), "--input-language", "en", "--output-language", "en", "--json"],
        ["report", "--results", str(results_path), "--out", str(report_out), "--json"],
        ["gate", "--results", str(results_path), "--config", str(gate_config), "--out", str(gate_out), "--json"],
        ["evidence-pack", "--results", str(results_path), "--out-dir", str(evidence_dir), "--classification", "fixture", "--copy-results", "--json"],
        ["compare", "--baseline", str(baseline_path), "--current", str(current_path), "--out", str(compare_out), "--json"],
        ["retry-audit", "--results", str(retry_path), "--out", str(retry_out), "--json"],
        ["models", "--min-models", "1", "--min-families", "1", "--min-size-bands", "1", "--out", str(model_out), "--json"],
        ["triage", "--results", str(results_path), "--expected-models", str(expected_models), "--out", str(triage_out), "--json"],
        ["agent-tools", "--list", "--json"],
        ["agent-tools", "--call", "mbs.validate", "--args", json.dumps({"schema_path": str(schema_path), "output_path": str(output_path)}), "--json"],
        ["adapt-responses", "--schema", str(schema_path), "--cases", str(cases_path), "--responses", str(responses_path), "--out", str(adapted_out), "--json"],
        ["make-response-template", "--cases", str(cases_path), "--out", str(template_out), "--json"],
    ]

    for argv in commands:
        assert main(argv) == 0, argv
        captured = capsys.readouterr()
        assert "Traceback" not in captured.out
        assert "Traceback" not in captured.err

    assert trace_out.exists()
    assert bench_out.exists()
    assert report_out.exists()
    assert gate_out.exists()
    assert (evidence_dir / "manifest.json").exists()
    assert compare_out.exists()
    assert retry_out.exists()
    assert triage_out.exists()
    assert adapted_out.exists()
    assert template_out.exists()
    assert model_out.exists()


def test_adapt_response_jsonl_creates_traceable_rows(tmp_path):
    schema_path = tmp_path / "schema.json"
    responses_path = tmp_path / "responses.jsonl"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    responses_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "case_id": "ok",
                        "input": "high risk transfer",
                        "output": {"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"},
                        "expected_valid_outputs": {"decision": "REVIEW"},
                        "tokens": {"mbs_contract": 5, "output": 7},
                    }
                ),
                json.dumps(
                    {
                        "case_id": "bad_enum",
                        "response": {"decision": "ALLOW", "risk_level": "LOW", "reason": "bad enum"},
                        "expected_valid_outputs": {"decision": "BLOCK"},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = adapt_response_jsonl(schema_path, responses_path, model="provider-x", decoding_mode="json_mode")

    assert result["summary"]["runs"] == 2
    assert result["summary"]["schema_valid_rate"] == 0.5
    assert result["summary"]["semantic_correct_rate"] == 0.5
    assert result["rows"][0]["trace"]["trace_id"].startswith("mbs_trace_")
    assert result["rows"][0]["tokens"]["output"] == 7
    assert result["rows"][1]["failure_type"] == "invented_enum"


def test_adapt_response_jsonl_marks_provider_errors_as_infra_failures(tmp_path):
    schema_path = tmp_path / "schema.json"
    responses_path = tmp_path / "responses.jsonl"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    responses_path.write_text(
        json.dumps(
            {
                "case_id": "infra",
                "input": "high risk transfer",
                "response": "",
                "provider_error": "DeploymentNotFound",
                "provider_error_message": "deployment missing",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = adapt_response_jsonl(schema_path, responses_path, model="provider-x", decoding_mode="tool_call")
    row = result["rows"][0]

    assert row["status"] == "INFRA_FAIL"
    assert row["infra_failure"] == "DeploymentNotFound"
    assert row["failure_type"] == "DeploymentNotFound"
    assert row["errors"][0]["message"] == "deployment missing"


def test_cli_adapt_responses_writes_reportable_result(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    cases_path = tmp_path / "cases.jsonl"
    responses_path = tmp_path / "responses.jsonl"
    out_path = tmp_path / "adapted.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    cases_path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "input": "high risk transfer",
                "expected_valid_outputs": {"risk_level": "HIGH"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    responses_path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "tool_call": {
                    "function": {
                        "name": "risk_review",
                        "arguments": {"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"},
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--responses",
                str(responses_path),
                "--cases",
                str(cases_path),
                "--model",
                "provider-x",
                "--decoding-mode",
                "tool_call",
                "--out",
                str(out_path),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    written = json.loads(out_path.read_text(encoding="utf-8"))

    assert payload["rows"][0]["decoding_mode"] == "tool_call"
    assert payload["rows"][0]["semantic_correct"] is True
    assert written["summary"]["schema_valid_rate"] == 1.0
    assert written["rows"][0]["trace"]["model"] == "provider-x"


def test_cli_json_readers_accept_windows_bom_and_crlf(tmp_path, capsys):
    schema_path = tmp_path / "schema_bom.json"
    output_path = tmp_path / "output_bom.json"
    records_path = tmp_path / "records_bom.jsonl"
    gate_config = tmp_path / "gate_bom.yaml"
    result_path = tmp_path / "result_bom.json"

    schema_path.write_text("\ufeff" + json.dumps(SCHEMA).replace(", ", ",\r\n"), encoding="utf-8")
    output_path.write_text(
        "\ufeff" + json.dumps({"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"}),
        encoding="utf-8",
    )
    records_path.write_text(
        "\ufeff" + json.dumps({"schema_valid": True, "tokens": {"output": 10}}) + "\r\n",
        encoding="utf-8",
    )
    result_path.write_text(
        "\ufeff"
        + json.dumps(
            {
                "schema": str(schema_path),
                "model": "bom-model",
                "summary": {
                    "runs": 1,
                    "schema_valid_rate": 1.0,
                    "semantic_correct_rate": 1.0,
                    "clean_json_rate": 1.0,
                },
                "rows": [
                    {
                        "case_id": "bom-case",
                        "schema_valid": True,
                        "json_valid": True,
                        "semantic_correct": True,
                        "trace": {"trace_id": "mbs_trace_bom", "tokens": {"output": 10}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    gate_config.write_text(
        "\ufeffthresholds:\r\n  min_schema_valid_rate: 1.0\r\n  min_semantic_correct_rate: 1.0\r\n  min_clean_json_rate: 1.0\r\n",
        encoding="utf-8",
    )

    assert main(["validate", "--schema", str(schema_path), "--output", str(output_path), "--json"]) == 0
    validate_payload = json.loads(capsys.readouterr().out)
    assert validate_payload["status"] == "PASS"

    assert main(["cost", "--results", str(records_path), "--json"]) == 0
    cost_payload = json.loads(capsys.readouterr().out)
    assert cost_payload["valid_outputs"] == 1

    assert main(["report", "--results", str(result_path), "--json"]) == 0
    report_payload = json.loads(capsys.readouterr().out)
    assert report_payload["summary"]["traceable_case_rows"] == 1

    assert main(["gate", "--results", str(result_path), "--config", str(gate_config), "--json"]) == 0
    gate_payload = json.loads(capsys.readouterr().out)
    assert gate_payload["status"] == "PASS"


def test_cli_invalid_json_file_returns_controlled_error(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    bad_output_path = tmp_path / "bad_output.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    bad_output_path.write_text('{"decision": "REVIEW",', encoding="utf-8")

    assert main(["validate", "--schema", str(schema_path), "--output", str(bad_output_path), "--json"]) == 2
    captured = capsys.readouterr()

    assert captured.out == ""
    assert "MBS input error: invalid JSON" in captured.err
    assert "bad_output.json" in captured.err
    assert "Traceback" not in captured.err


def test_cli_validate_routine_file_mistakes_do_not_traceback(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    invalid_schema_path = tmp_path / "invalid_schema.json"
    missing_schema_path = tmp_path / "missing_schema.json"
    missing_output_path = tmp_path / "missing_output.json"

    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    invalid_schema_path.write_text(json.dumps(["not", "a", "schema", "object"]), encoding="utf-8")

    cases = [
        (
            ["validate", "--schema", str(missing_schema_path), "--output", "{}", "--json"],
            "schema file not found",
        ),
        (
            ["validate", "--schema", str(schema_path), "--output", str(missing_output_path), "--json"],
            "JSON file not found",
        ),
        (
            ["validate", "--schema", str(invalid_schema_path), "--output", "{}", "--json"],
            "schema must be a JSON object",
        ),
    ]

    for argv, expected in cases:
        assert main(argv) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "MBS input error:" in captured.err
        assert expected in captured.err
        assert "Traceback" not in captured.err


def test_cli_json_outputs_include_agent_contract_fields(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    valid_output_path = tmp_path / "valid_output.json"
    invalid_output_path = tmp_path / "invalid_output.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    valid_output_path.write_text(
        json.dumps({"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"}),
        encoding="utf-8",
    )
    invalid_output_path.write_text(
        json.dumps({"decision": "ALLOW", "risk_level": "LOW", "reason": "bad enum"}),
        encoding="utf-8",
    )

    assert main(["validate", "--schema", str(schema_path), "--output", str(invalid_output_path), "--json"]) == 2
    validate_payload = json.loads(capsys.readouterr().out)
    assert validate_payload["status"] == "FAIL"
    assert validate_payload["failure_reason"] == "invented_enum"

    assert (
        main(
            [
                "check",
                "--schema",
                str(schema_path),
                "--output",
                str(valid_output_path),
                "--model",
                "contract-model",
                "--json",
            ]
        )
        == 0
    )
    check_payload = json.loads(capsys.readouterr().out)
    assert check_payload["status"] == "PASS"
    assert check_payload["failure_reason"] is None
    assert check_payload["trace_id"].startswith("mbs_trace_")
    assert check_payload["trace"]["trace_id"] == check_payload["trace_id"]
    assert check_payload["trace"]["failure_reason"] is None
    assert check_payload["schema_hash"].startswith("sha256:")
    assert check_payload["contract_hash"].startswith("sha256:")

    assert (
        main(
            [
                "check",
                "--schema",
                str(schema_path),
                "--output",
                str(invalid_output_path),
                "--model",
                "contract-model",
                "--json",
            ]
        )
        == 2
    )
    invalid_check_payload = json.loads(capsys.readouterr().out)
    assert invalid_check_payload["status"] == "FAIL"
    assert invalid_check_payload["failure_reason"] == "invented_enum"
    assert invalid_check_payload["trace"]["failure_reason"] == "invented_enum"


def test_cli_trace_outputs_create_parent_directories(tmp_path):
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "output.json"
    trace_out_path = tmp_path / "nested" / "check" / "trace.json"
    direct_trace_path = tmp_path / "nested" / "trace" / "trace.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    output_path.write_text(
        json.dumps({"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"}),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "check",
                "--schema",
                str(schema_path),
                "--output",
                str(output_path),
                "--trace-out",
                str(trace_out_path),
                "--json",
            ]
        )
        == 0
    )
    assert main(["trace", "--schema", str(schema_path), "--output", str(output_path), "--out", str(direct_trace_path)]) == 0

    assert json.loads(trace_out_path.read_text(encoding="utf-8"))["trace_id"].startswith("mbs_trace_")
    assert json.loads(direct_trace_path.read_text(encoding="utf-8"))["trace_id"].startswith("mbs_trace_")


def test_cli_routine_misuse_returns_controlled_errors(tmp_path, capsys):
    bad_config_path = tmp_path / "bad_config.json"
    list_config_path = tmp_path / "list_config.json"
    bad_yaml_path = tmp_path / "bad_config.yaml"
    bad_records_path = tmp_path / "bad_records.jsonl"
    nonobject_records_path = tmp_path / "nonobject_records.jsonl"

    bad_config_path.write_text('{"schema":', encoding="utf-8")
    list_config_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    bad_yaml_path.write_text("not a supported yaml line", encoding="utf-8")
    bad_records_path.write_text('{"schema_valid": true\n', encoding="utf-8")
    nonobject_records_path.write_text(json.dumps(["not-object"]) + "\n", encoding="utf-8")

    stderr_cases = [
        (["cost", "--json"], "mbs cost requires"),
        (["bench", "--config", str(bad_config_path), "--json"], "invalid JSON"),
        (["bench", "--config", str(list_config_path), "--json"], "MBS config must be"),
        (["bench", "--config", str(bad_yaml_path), "--json"], ("Unsupported YAML config line", "MBS YAML config must be an object")),
        (["cost", "--results", str(bad_records_path), "--json"], "invalid JSON"),
        (["cost", "--results", str(nonobject_records_path), "--json"], "JSON array record must be an object"),
        (["agent-tools", "--call", "mbs.validate", "--args", '["not", "object"]', "--json"], "MBS config must be"),
    ]

    for argv, expected in stderr_cases:
        assert main(argv) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "MBS input error:" in captured.err
        if isinstance(expected, tuple):
            assert any(item in captured.err for item in expected)
        else:
            assert expected in captured.err
        assert "Traceback" not in captured.err

    for argv, expected in [
        (["agent-tools", "--call", "mbs.no_such_tool", "--json"], "Unknown MBS agent tool"),
        (["agent-tools", "--request", '{"tool": "mbs.check"}', "--json"], "requires schema or schema_path"),
    ]:
        assert main(argv) == 2
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert expected in payload["error"]["message"]
        assert captured.err == ""
        assert "Traceback" not in captured.out


def test_cli_edge_command_matrix_returns_controlled_errors(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    output_path = tmp_path / "output.json"
    cases_path = tmp_path / "cases.jsonl"
    result_path = tmp_path / "result.json"
    empty_results_path = tmp_path / "empty_results.json"
    bad_gate_config_path = tmp_path / "bad_gate.json"
    registry_path = tmp_path / "registry.json"
    template_path = tmp_path / "template.jsonl"
    trace_out_path = tmp_path / "trace.json"

    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    output_path.write_text(
        json.dumps({"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"}),
        encoding="utf-8",
    )
    cases_path.write_text(json.dumps({"id": "case-1", "input": "review transfer"}) + "\n", encoding="utf-8")
    result_path.write_text(
        json.dumps(
            {
                "schema": str(schema_path),
                "model": "edge-model",
                "summary": {"runs": 1, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0, "clean_json_rate": 1.0},
                "rows": [
                    {
                        "case_id": "case-1",
                        "schema_valid": True,
                        "json_valid": True,
                        "semantic_correct": True,
                        "trace": {"trace_id": "mbs_trace_edge", "tokens": {"output": 3}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    empty_results_path.write_text(json.dumps({"rows": []}), encoding="utf-8")
    bad_gate_config_path.write_text(json.dumps(["not", "a", "config", "object"]), encoding="utf-8")
    registry_path.write_text(json.dumps({"suites": {"tiny": []}, "models": {}}), encoding="utf-8")

    cases = [
        (["compile", str(tmp_path / "missing_schema.json"), "--json"], "schema file not found"),
        (["check", "--schema", str(schema_path), "--output", str(tmp_path / "missing_output.json"), "--json"], "JSON file not found"),
        (["trace", "--schema", str(schema_path), "--output", str(tmp_path / "missing_output.json"), "--out", str(trace_out_path)], "JSON file not found"),
        (["cost", "--results", str(tmp_path / "missing_records.jsonl"), "--json"], "records file not found"),
        (["bench", "--schema", str(schema_path), "--cases", str(tmp_path / "missing_cases.jsonl"), "--json"], "No such file"),
        (["test", "--schemas", str(tmp_path / "missing_schemas"), "--cases", str(cases_path), "--json"], "no schema files found"),
        (["lang", str(tmp_path / "missing_schema.json"), "--input-language", "en", "--output-language", "en", "--json"], "schema file not found"),
        (["report", "--results", str(tmp_path / "missing_result.json"), "--json"], None),
        (["gate", "--results", str(result_path), "--config", str(bad_gate_config_path), "--json"], "MBS gate config must be an object"),
        (["evidence-pack", "--results", str(empty_results_path), "--out-dir", str(tmp_path / "evidence"), "--json"], "no result rows found"),
        (["compare", "--baseline", str(tmp_path / "missing_base.json"), "--current", str(result_path), "--json"], None),
        (["retry-audit", "--results", str(tmp_path / "missing_retry.json"), "--json"], "no retry result rows found"),
        (["models", "--registry", str(registry_path), "--suite", "missing", "--json"], "Unknown model suite"),
        (["triage", "--results", str(tmp_path / "missing_result.json"), "--json"], "no result rows found"),
        (["adapt-responses", "--schema", str(schema_path), "--responses", str(tmp_path / "missing_responses.jsonl"), "--json"], "No such file"),
        (["make-response-template", "--cases", str(tmp_path / "missing_cases.jsonl"), "--out", str(template_path), "--json"], "No such file"),
    ]

    for argv, expected in cases:
        assert main(argv) == 2, argv
        captured = capsys.readouterr()
        if expected is None:
            assert captured.out
            assert captured.err == ""
        else:
            assert captured.out == ""
            assert "MBS input error:" in captured.err
            assert expected in captured.err
        assert "Traceback" not in captured.err


def test_cli_artifact_commands_accept_bom_encoded_inputs(tmp_path, capsys):
    schema_path = tmp_path / "schema_bom.json"
    cases_path = tmp_path / "cases_bom.jsonl"
    responses_path = tmp_path / "responses_bom.jsonl"
    baseline_path = tmp_path / "baseline_bom.json"
    current_path = tmp_path / "current_bom.json"
    retry_path = tmp_path / "retry_bom.json"
    expected_models_path = tmp_path / "expected_models_bom.txt"
    adapted_path = tmp_path / "adapted.json"
    evidence_dir = tmp_path / "evidence"

    schema_path.write_text("\ufeff" + json.dumps(SCHEMA), encoding="utf-8")
    cases_path.write_text(
        "\ufeff"
        + json.dumps(
            {
                "id": "case-1",
                "input": "high risk transfer",
                "expected_valid_outputs": {"risk_level": "HIGH"},
            }
        )
        + "\r\n",
        encoding="utf-8",
    )
    responses_path.write_text(
        "\ufeff"
        + json.dumps(
            {
                "id": "case-1",
                "output": {"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"},
            }
        )
        + "\r\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(responses_path),
                "--model",
                "bom-provider",
                "--out",
                str(adapted_path),
                "--json",
            ]
        )
        == 0
    )
    adapted_payload = json.loads(capsys.readouterr().out)
    assert adapted_payload["summary"]["schema_valid_rate"] == 1.0

    adapted_text = adapted_path.read_text(encoding="utf-8")
    baseline_path.write_text("\ufeff" + adapted_text, encoding="utf-8")
    current_path.write_text("\ufeff" + adapted_text, encoding="utf-8")
    expected_models_path.write_text("\ufeffbom-provider\r\n", encoding="utf-8")
    retry_path.write_text(
        "\ufeff"
        + json.dumps(
            {
                "model": "bom-provider",
                "rows": [
                    {
                        "case_id": "retry-1",
                        "retry_count": 1,
                        "attempts": [
                            {"attempt": 0, "json_valid": True, "schema_valid": False, "semantic_correct": False},
                            {
                                "attempt": 1,
                                "selected": True,
                                "json_valid": True,
                                "schema_valid": True,
                                "semantic_correct": True,
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["compare", "--baseline", str(baseline_path), "--current", str(current_path), "--json"]) == 0
    compare_payload = json.loads(capsys.readouterr().out)
    assert compare_payload["status"] == "PASS"

    assert main(["triage", "--results", str(current_path), "--expected-models", str(expected_models_path), "--json"]) == 0
    triage_payload = json.loads(capsys.readouterr().out)
    assert triage_payload["missing_models"] == []

    assert main(["retry-audit", "--results", str(retry_path), "--json"]) == 0
    retry_payload = json.loads(capsys.readouterr().out)
    assert retry_payload["status"] == "PASS"
    assert retry_payload["improved_rows"] == 1

    assert (
        main(
            [
                "evidence-pack",
                "--results",
                str(current_path),
                "--out-dir",
                str(evidence_dir),
                "--classification",
                "fixture",
                "--copy-results",
                "--json",
            ]
        )
        == 0
    )
    evidence_payload = json.loads(capsys.readouterr().out)
    assert evidence_payload["checks"]["report_rows"] == 1
    assert (evidence_dir / "manifest.json").exists()


def test_public_adapter_fixture_supports_report_and_compare(tmp_path):
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "examples" / "tool_argument_generation" / "schema.json"
    cases_path = root / "examples" / "tool_argument_generation" / "cases.jsonl"
    text_responses = root / "examples" / "tool_argument_generation" / "provider_text_responses.jsonl"
    tool_responses = root / "examples" / "tool_argument_generation" / "provider_tool_call_responses.jsonl"
    text_out = tmp_path / "text.json"
    tool_out = tmp_path / "tool_call.json"

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(text_responses),
                "--model",
                "fixture-provider",
                "--decoding-mode",
                "text",
                "--out",
                str(text_out),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(tool_responses),
                "--model",
                "fixture-provider",
                "--decoding-mode",
                "tool_call",
                "--out",
                str(tool_out),
                "--json",
            ]
        )
        == 0
    )

    report = aggregate_results([tool_out])
    comparison = compare_results([text_out], [tool_out], key_fields=["schema", "model", "language"])

    assert report["summary"]["traceable_case_rows"] == 2
    assert report["summary"]["missing_trace_rows"] == 0
    assert report["rows"][0]["schema_valid_rate"] == 1.0
    assert comparison["status"] == "PASS"
    assert any(item["metric"] == "schema_valid_rate" and item["delta"] > 0 for item in comparison["comparisons"])


def test_provider_json_mode_fixture_supports_gate_and_evidence_pack(tmp_path):
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "examples" / "tool_argument_generation" / "schema.json"
    cases_path = root / "examples" / "tool_argument_generation" / "cases.jsonl"
    json_mode_responses = root / "examples" / "tool_argument_generation" / "provider_json_mode_responses.jsonl"
    gate_config = root / "benchmarks" / "fixture_smoke_gate.yaml"
    out_path = tmp_path / "provider_json_mode.mbs.json"
    pack_dir = tmp_path / "evidence_pack"

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(json_mode_responses),
                "--model",
                "fixture-provider-json-mode",
                "--decoding-mode",
                "json_mode",
                "--out",
                str(out_path),
                "--json",
            ]
        )
        == 0
    )
    assert main(["gate", "--results", str(out_path), "--config", str(gate_config), "--json"]) == 0
    assert (
        main(
            [
                "evidence-pack",
                "--results",
                str(out_path),
                "--gate-config",
                str(gate_config),
                "--classification",
                "fixture",
                "--copy-results",
                "--out-dir",
                str(pack_dir),
            ]
        )
        == 0
    )
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["summary"]["schema_valid_rate"] == 1.0
    assert payload["summary"]["semantic_correct_rate"] == 1.0
    assert manifest["classification"] == "fixture_smoke_not_provider_benchmark"
    assert manifest["checks"]["gate_status"] == "PASS"


def test_incident_response_workflow_pack_passes_and_fails_with_evidence(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workflow_dir = root / "examples" / "incident_response_runbook"
    schema_path = workflow_dir / "schema.json"
    cases_path = workflow_dir / "cases.jsonl"
    good_responses = workflow_dir / "provider_good_responses.jsonl"
    bad_responses = workflow_dir / "provider_bad_responses.jsonl"
    gate_config = root / "benchmarks" / "incident_response_gate.yaml"
    good_out = tmp_path / "incident_good.mbs.json"
    bad_out = tmp_path / "incident_bad.mbs.json"
    pack_dir = tmp_path / "incident_evidence_pack"

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(good_responses),
                "--model",
                "incident-good-fixture",
                "--decoding-mode",
                "json_mode",
                "--out",
                str(good_out),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(bad_responses),
                "--model",
                "incident-bad-fixture",
                "--decoding-mode",
                "json_mode",
                "--out",
                str(bad_out),
                "--json",
            ]
        )
        == 0
    )

    good_payload = json.loads(good_out.read_text(encoding="utf-8"))
    bad_payload = json.loads(bad_out.read_text(encoding="utf-8"))
    bad_failure_types = {row["case_id"]: row["failure_type"] for row in bad_payload["rows"]}

    assert good_payload["summary"]["runs"] == 8
    assert good_payload["summary"]["schema_valid_rate"] == 1.0
    assert good_payload["summary"]["semantic_correct_rate"] == 1.0
    assert good_payload["summary"]["clean_json_rate"] == 1.0
    assert main(["gate", "--results", str(good_out), "--config", str(gate_config), "--json"]) == 0
    assert (
        main(
            [
                "evidence-pack",
                "--results",
                str(good_out),
                "--gate-config",
                str(gate_config),
                "--classification",
                "fixture",
                "--copy-results",
                "--out-dir",
                str(pack_dir),
                "--json",
            ]
        )
        == 0
    )

    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["classification"] == "fixture_smoke_not_provider_benchmark"
    assert manifest["checks"]["gate_status"] == "PASS"
    assert manifest["checks"]["report_rows"] == 1
    assert (pack_dir / "raw_results" / "incident_good.mbs.json").exists()

    assert bad_payload["summary"]["runs"] == 8
    assert bad_payload["summary"]["schema_valid_rate"] < 0.6
    assert bad_payload["summary"]["semantic_correct_rate"] < 0.5
    assert bad_failure_types["ir_001"] == "semantic_mismatch"
    assert bad_failure_types["ir_002"] == "invented_enum"
    assert bad_failure_types["ir_003"] == "wrong_type"
    assert bad_failure_types["ir_004"] == "extra_key"
    assert bad_failure_types["ir_006"] == "const_mismatch"
    assert main(["gate", "--results", str(bad_out), "--config", str(gate_config), "--json"]) == 2


def test_fintech_transaction_risk_workflow_pack_passes_and_fails_with_evidence(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workflow_dir = root / "examples" / "fintech_transaction_risk"
    schema_path = workflow_dir / "schema.json"
    cases_path = workflow_dir / "cases.jsonl"
    good_responses = workflow_dir / "provider_good_responses.jsonl"
    bad_responses = workflow_dir / "provider_bad_responses.jsonl"
    gate_config = root / "benchmarks" / "fintech_transaction_risk_gate.yaml"
    good_out = tmp_path / "fintech_good.mbs.json"
    bad_out = tmp_path / "fintech_bad.mbs.json"
    pack_dir = tmp_path / "fintech_evidence_pack"

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(good_responses),
                "--model",
                "fintech-good-fixture",
                "--decoding-mode",
                "json_mode",
                "--out",
                str(good_out),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(bad_responses),
                "--model",
                "fintech-bad-fixture",
                "--decoding-mode",
                "json_mode",
                "--out",
                str(bad_out),
                "--json",
            ]
        )
        == 0
    )

    good_payload = json.loads(good_out.read_text(encoding="utf-8"))
    bad_payload = json.loads(bad_out.read_text(encoding="utf-8"))
    bad_failure_types = {row["case_id"]: row["failure_type"] for row in bad_payload["rows"]}

    assert good_payload["summary"]["runs"] == 8
    assert good_payload["summary"]["schema_valid_rate"] == 1.0
    assert good_payload["summary"]["semantic_correct_rate"] == 1.0
    assert good_payload["summary"]["clean_json_rate"] == 1.0
    assert main(["gate", "--results", str(good_out), "--config", str(gate_config), "--json"]) == 0
    assert (
        main(
            [
                "evidence-pack",
                "--results",
                str(good_out),
                "--gate-config",
                str(gate_config),
                "--classification",
                "fixture",
                "--copy-results",
                "--out-dir",
                str(pack_dir),
                "--json",
            ]
        )
        == 0
    )

    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["classification"] == "fixture_smoke_not_provider_benchmark"
    assert manifest["checks"]["gate_status"] == "PASS"
    assert manifest["checks"]["report_rows"] == 1
    assert (pack_dir / "raw_results" / "fintech_good.mbs.json").exists()

    assert bad_payload["summary"]["runs"] == 8
    assert bad_payload["summary"]["schema_valid_rate"] < 0.4
    assert bad_payload["summary"]["semantic_correct_rate"] < 0.5
    assert bad_failure_types["risk_001"] == "semantic_mismatch"
    assert bad_failure_types["risk_002"] == "invented_enum"
    assert bad_failure_types["risk_003"] == "wrong_type"
    assert bad_failure_types["risk_004"] == "extra_key"
    assert bad_failure_types["risk_008"] == "missing_required_key"
    assert main(["gate", "--results", str(bad_out), "--config", str(gate_config), "--json"]) == 2


def test_support_ticket_triage_workflow_pack_passes_and_fails_with_evidence(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workflow_dir = root / "examples" / "support_ticket_triage"
    schema_path = workflow_dir / "schema.json"
    cases_path = workflow_dir / "cases.jsonl"
    good_responses = workflow_dir / "provider_good_responses.jsonl"
    bad_responses = workflow_dir / "provider_bad_responses.jsonl"
    gate_config = root / "benchmarks" / "support_ticket_triage_gate.yaml"
    good_out = tmp_path / "support_good.mbs.json"
    bad_out = tmp_path / "support_bad.mbs.json"
    pack_dir = tmp_path / "support_evidence_pack"

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(good_responses),
                "--model",
                "support-good-fixture",
                "--decoding-mode",
                "json_mode",
                "--out",
                str(good_out),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(bad_responses),
                "--model",
                "support-bad-fixture",
                "--decoding-mode",
                "json_mode",
                "--out",
                str(bad_out),
                "--json",
            ]
        )
        == 0
    )

    good_payload = json.loads(good_out.read_text(encoding="utf-8"))
    bad_payload = json.loads(bad_out.read_text(encoding="utf-8"))
    bad_failure_types = {row["case_id"]: row["failure_type"] for row in bad_payload["rows"]}

    assert good_payload["summary"]["runs"] == 8
    assert good_payload["summary"]["schema_valid_rate"] == 1.0
    assert good_payload["summary"]["semantic_correct_rate"] == 1.0
    assert good_payload["summary"]["clean_json_rate"] == 1.0
    assert main(["gate", "--results", str(good_out), "--config", str(gate_config), "--json"]) == 0
    assert (
        main(
            [
                "evidence-pack",
                "--results",
                str(good_out),
                "--gate-config",
                str(gate_config),
                "--classification",
                "fixture",
                "--copy-results",
                "--out-dir",
                str(pack_dir),
                "--json",
            ]
        )
        == 0
    )

    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["classification"] == "fixture_smoke_not_provider_benchmark"
    assert manifest["checks"]["gate_status"] == "PASS"
    assert manifest["checks"]["report_rows"] == 1
    assert (pack_dir / "raw_results" / "support_good.mbs.json").exists()

    assert bad_payload["summary"]["runs"] == 8
    assert bad_payload["summary"]["schema_valid_rate"] < 0.5
    assert bad_payload["summary"]["semantic_correct_rate"] < 0.5
    assert bad_failure_types["support_001"] == "semantic_mismatch"
    assert bad_failure_types["support_002"] == "invented_enum"
    assert bad_failure_types["support_003"] == "wrong_type"
    assert bad_failure_types["support_004"] == "extra_key"
    assert bad_failure_types["support_008"] == "missing_required_key"
    assert main(["gate", "--results", str(bad_out), "--config", str(gate_config), "--json"]) == 2


def test_nested_tool_argument_fixtures_separate_schema_and_semantic_failures(tmp_path):
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "examples" / "nested_tool_arguments" / "schema.json"
    cases_path = root / "examples" / "nested_tool_arguments" / "cases.jsonl"
    good_responses = root / "examples" / "nested_tool_arguments" / "provider_tool_call_good.jsonl"
    bad_responses = root / "examples" / "nested_tool_arguments" / "provider_tool_call_bad.jsonl"
    good_out = tmp_path / "nested_good.mbs.json"
    bad_out = tmp_path / "nested_bad.mbs.json"

    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(good_responses),
                "--model",
                "nested-tool-good-fixture",
                "--decoding-mode",
                "tool_call",
                "--out",
                str(good_out),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "adapt-responses",
                "--schema",
                str(schema_path),
                "--cases",
                str(cases_path),
                "--responses",
                str(bad_responses),
                "--model",
                "nested-tool-bad-fixture",
                "--decoding-mode",
                "tool_call",
                "--out",
                str(bad_out),
                "--json",
            ]
        )
        == 0
    )
    good_payload = json.loads(good_out.read_text(encoding="utf-8"))
    bad_payload = json.loads(bad_out.read_text(encoding="utf-8"))
    first_bad_errors = bad_payload["rows"][0]["errors"]
    failure_types = {row["case_id"]: row["failure_type"] for row in bad_payload["rows"]}
    nested_004_errors = bad_payload["rows"][3]["errors"]
    nested_005_errors = bad_payload["rows"][4]["errors"]
    nested_006_errors = bad_payload["rows"][5]["errors"]

    assert good_payload["summary"]["schema_valid_rate"] == 1.0
    assert good_payload["summary"]["semantic_correct_rate"] == 1.0
    assert bad_payload["summary"]["runs"] == 25
    assert bad_payload["summary"]["schema_valid_rate"] == 0.72
    assert bad_payload["summary"]["semantic_correct_rate"] == 0.2
    assert {"field": "customer.verified", "type": "wrong_type", "expected": "boolean", "received": "str"} in first_bad_errors
    assert {"field": "actions[0].currency", "type": "missing_required_key"} in first_bad_errors
    assert {"field": "actions[0].amount", "type": "wrong_type", "expected": "number", "received": "str"} in first_bad_errors
    assert bad_payload["rows"][0]["semantic_correct"] is True
    assert bad_payload["rows"][1]["schema_valid"] is True
    assert bad_payload["rows"][1]["semantic_correct"] is False
    assert failure_types["nested_002"] == "semantic_mismatch"
    assert failure_types["nested_003"] == "prose_wrapped_json"
    assert {"field": "customer.tier", "type": "extra_key"} in nested_004_errors
    assert {"field": "actions[0].memo", "type": "extra_key"} in nested_004_errors
    assert {"field": "debug", "type": "extra_key"} in nested_004_errors
    assert nested_005_errors[0]["hint"] == "joined_enum_values"
    assert nested_006_errors[0]["hint"] == "case_mismatch"


def test_adapter_fixture_gate_script_writes_manifest(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_adapter_fixture_gate.py"
    spec = importlib.util.spec_from_file_location("run_adapter_fixture_gate", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        "sys.argv",
        ["run_adapter_fixture_gate.py", "--root", str(root), "--out-dir", str(tmp_path), "--json"],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert manifest["classification"] == "adapter_fixture_smoke_not_provider_benchmark"
    assert manifest["checks"]["compare_status"] == "PASS"
    assert manifest["checks"]["triage_status"] == "FAIL"
    assert manifest["checks"]["expected_fixture_failures_present"] is True
    assert (tmp_path / "report_summary.md").exists()


def test_nested_tool_fixture_pack_script_writes_evidence_packs(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_nested_tool_fixture_pack.py"
    spec = importlib.util.spec_from_file_location("run_nested_tool_fixture_pack", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        "sys.argv",
        ["run_nested_tool_fixture_pack.py", "--root", str(root), "--out-dir", str(tmp_path), "--json"],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert manifest["classification"] == "fixture_smoke_not_provider_benchmark"
    assert manifest["checks"]["nested_schema_error_present"] is True
    assert manifest["checks"]["strict_extra_key_error_present"] is True
    assert manifest["checks"]["joined_enum_error_present"] is True
    assert manifest["checks"]["case_mismatch_error_present"] is True
    assert manifest["checks"]["prose_wrapped_json_warning_present"] is True
    assert manifest["checks"]["semantic_mismatch_present"] is True
    assert (tmp_path / "evidence_pack_good" / "manifest.json").exists()
    assert (tmp_path / "evidence_pack_bad" / "triage.json").exists()
    assert (tmp_path / "evidence_pack_bad" / "report.md").exists()
    assert (tmp_path / "evidence_pack_good" / "report.md").exists()


def test_nested_provider_evidence_script_classifies_fixture_pack(tmp_path):
    script = Path("scripts/build_nested_provider_evidence.py")
    spec = importlib.util.spec_from_file_location("build_nested_provider_evidence", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    out_dir = tmp_path / "nested_provider_pack"
    old_argv = sys.argv
    try:
        sys.argv = [
            str(script),
            "--responses",
            "examples/nested_tool_arguments/provider_tool_call_good.jsonl",
            "--out-dir",
            str(out_dir),
            "--model",
            "fixture-nested-tool-provider",
            "--decoding-mode",
            "tool_call",
            "--classification",
            "fixture",
            "--json",
        ]
        assert module.main() == 0
    finally:
        sys.argv = old_argv

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    pack_manifest = json.loads((out_dir / "evidence_pack" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "PASS"
    assert manifest["classification_label"] == "fixture_smoke_not_provider_benchmark"
    assert manifest["checks"]["gate_status"] == "PASS"
    assert manifest["checks"]["trace_errors"] == []
    assert pack_manifest["classification"] == "fixture_smoke_not_provider_benchmark"
    assert (out_dir / "nested_provider.mbs.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "gate.json").exists()
    assert (out_dir / "triage.json").exists()
    assert (out_dir / "evidence_pack" / "raw_results" / "nested_provider.mbs.json").exists()


def test_nested_provider_runner_reuses_existing_responses(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_nested_provider_evidence.py"
    spec = importlib.util.spec_from_file_location("run_nested_provider_evidence", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out_dir = tmp_path / "nested_provider_run"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_nested_provider_evidence.py",
            "--root",
            str(root),
            "--responses",
            str(root / "examples" / "nested_tool_arguments" / "provider_tool_call_good.jsonl"),
            "--out-dir",
            str(out_dir),
            "--model",
            "fixture-nested-tool-provider",
            "--mode",
            "tool_call",
            "--classification",
            "fixture",
            "--json",
        ],
    )

    assert module.main() == 0
    run_manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    evidence_manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))

    assert run_manifest["status"] == "PASS"
    assert run_manifest["collected_responses"] is False
    assert run_manifest["classification_label"] == "fixture_smoke_not_provider_benchmark"
    assert evidence_manifest["checks"]["gate_status"] == "PASS"
    assert (out_dir / "run_plan.json").exists()
    assert (out_dir / "evidence_pack" / "manifest.json").exists()


def test_nested_provider_runner_dry_run_uses_env_deployment_by_default(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_nested_provider_evidence.py"
    spec = importlib.util.spec_from_file_location("run_nested_provider_evidence_dry_run", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out_dir = tmp_path / "nested_provider_dry_run"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_nested_provider_evidence.py",
            "--root",
            str(root),
            "--out-dir",
            str(out_dir),
            "--model",
            "display-model-label",
            "--mode",
            "tool_call",
            "--classification",
            "provider",
            "--dry-run",
            "--json",
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    collect_command = payload["commands"][0]

    assert payload["status"] == "DRY_RUN"
    assert "--deployment" not in collect_command
    assert "--model" in collect_command
    assert collect_command[collect_command.index("--model") + 1] == "display-model-label"
    assert "--policy" in collect_command
    assert collect_command[collect_command.index("--policy") + 1].endswith("examples\\nested_tool_arguments\\policy.md") or collect_command[
        collect_command.index("--policy") + 1
    ].endswith("examples/nested_tool_arguments/policy.md")


def test_collect_azure_openai_responses_includes_policy_in_prompt(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "collect_azure_openai_responses.py"
    spec = importlib.util.spec_from_file_location("collect_azure_openai_responses", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    schema = {"type": "object", "properties": {"tool": {"type": "string"}}, "required": ["tool"]}
    case = {"input": "Verified customer asks for a refund."}
    body = module.build_request(schema, case, "json_mode", max_tokens=64, seed=333, policy="Choose create_refund for valid refunds.")
    user_message = body["messages"][1]["content"]

    assert "Task policy:" in user_message
    assert "Choose create_refund for valid refunds." in user_message
    assert body["response_format"] == {"type": "json_object"}


def test_provider_script_jsonl_loaders_accept_bom(tmp_path):
    root = Path(__file__).resolve().parents[1]
    cases_path = tmp_path / "cases_bom.jsonl"
    cases_path.write_text("\ufeff" + json.dumps({"id": "case-1", "input": "hello"}) + "\r\n", encoding="utf-8")

    for script_name in ["collect_azure_openai_responses.py", "collect_hf_local_responses.py", "make_tuning_dataset.py"]:
        script_path = root / "scripts" / script_name
        spec = importlib.util.spec_from_file_location(script_name.removesuffix(".py"), script_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        rows = module.load_jsonl(str(cases_path))

        assert rows == [{"id": "case-1", "input": "hello"}]


def test_nested_provider_runner_writes_manifest_on_gate_failure(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_nested_provider_evidence.py"
    spec = importlib.util.spec_from_file_location("run_nested_provider_evidence_fail", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out_dir = tmp_path / "nested_provider_failed_run"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_nested_provider_evidence.py",
            "--root",
            str(root),
            "--responses",
            str(root / "examples" / "nested_tool_arguments" / "provider_tool_call_bad.jsonl"),
            "--out-dir",
            str(out_dir),
            "--model",
            "fixture-nested-tool-provider-bad",
            "--mode",
            "tool_call",
            "--classification",
            "provider",
            "--json",
        ],
    )

    assert module.main() == 2
    run_manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    evidence_manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))

    assert run_manifest["status"] == "FAIL"
    assert run_manifest["gate_status"] == "FAIL"
    assert run_manifest["command_failures"][0]["returncode"] == 2
    assert evidence_manifest["checks"]["gate_status"] == "FAIL"
    assert (out_dir / "gate.json").exists()
    assert (out_dir / "triage.json").exists()


def test_provider_gate_requires_behavior_rows_when_configured(tmp_path):
    result_path = tmp_path / "infra_only.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "provider-x",
                "summary": {"runs": 1, "schema_valid_rate": 0.0, "semantic_correct_rate": 0.0, "clean_json_rate": 0.0},
                "rows": [
                    {
                        "status": "INFRA_FAIL",
                        "failure_type": "DeploymentNotFound",
                        "trace": {"trace_id": "mbs_trace_infra", "tokens": {"output": 1}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    gate = evaluate_gate(
        [result_path],
        config={
            "thresholds": {
                "min_schema_valid_rate": 0.0,
                "min_semantic_correct_rate": 0.0,
                "min_clean_json_rate": 0.0,
                "min_rows": 1,
                "min_behavior_rows": 1,
                "min_total_runs": 1,
                "max_infra_failed_rows": 1,
            }
        },
    )

    assert gate["status"] == "FAIL"
    assert gate["summary"]["behavior_rows"] == 0
    assert {"metric": "behavior_rows", "actual": 0, "required": ">= 1"} in gate["failures"]


def test_provider_matrix_summary_preserves_failed_gate_evidence():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "assert_provider_matrix_summary.py"
    spec = importlib.util.spec_from_file_location("assert_provider_matrix_summary", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    summary_path = root / "docs" / "provider_matrix_summary_20260514" / "provider_matrix_summary.json"
    result = module.validate_summary(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert result == {"status": "PASS", "failures": [], "rows": 3}
    assert summary["raw_artifacts_public"] is False
    assert {row["gate_status"] for row in summary["rows"]} == {"FAIL"}
    assert {row["primary_failure_mode"] for row in summary["rows"]} == {
        "schema_clean_semantic_mismatch",
        "format_schema_failure",
    }


def test_oss_hpc_dry_run_record_makes_no_evidence_claim():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "assert_oss_hpc_dry_run_record.py"
    spec = importlib.util.spec_from_file_location("assert_oss_hpc_dry_run_record", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    record_path = root / "docs" / "oss_hpc_endpoint_dry_run_20260514" / "endpoint_dry_run.json"
    result = module.validate_record(record_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))

    assert result == {"status": "PASS", "failures": [], "checked_urls": 3}
    assert record["status"] == "NO_EVIDENCE_DRY_RUN"
    assert record["endpoint_probe"]["reachable_endpoints"] == []
    assert record["evidence_boundary"]["raw_responses_collected"] is False
    assert record["evidence_boundary"]["evidence_pack_created"] is False
    assert record["evidence_boundary"]["aggregate_matrix_row_created"] is False


def test_nested_tool_suite_expanded_to_twenty_five_cases():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "assert_nested_tool_suite.py"
    spec = importlib.util.spec_from_file_location("assert_nested_tool_suite", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    result = module.validate_suite(root)

    assert result == {
        "status": "PASS",
        "failures": [],
        "case_count": 25,
        "good_rows": 25,
        "bad_rows": 25,
        "archived_case_count": 8,
    }


def test_nested_retry_matrix_reports_repair_policies(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_nested_retry_matrix.py"
    spec = importlib.util.spec_from_file_location("run_nested_retry_matrix", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        "sys.argv",
        ["run_nested_retry_matrix.py", "--root", str(root), "--out-dir", str(tmp_path), "--json"],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    matrix = json.loads((tmp_path / "retry_matrix_summary.json").read_text(encoding="utf-8"))
    audit = json.loads((tmp_path / "retry_audit.json").read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert payload["classification"] == "fixture_retry_matrix_not_provider_benchmark"
    assert payload["checks"]["case_count"] == 25
    assert payload["checks"]["no_retry_schema_valid_rate"] == 0.72
    assert payload["checks"]["no_retry_semantic_correct_rate"] == 0.2
    assert payload["checks"]["mbs_retry_schema_valid_rate"] == 1.0
    assert payload["checks"]["mbs_retry_semantic_correct_rate"] == 1.0
    assert payload["checks"]["format_retry_schema_valid_rate"] == 1.0
    assert payload["checks"]["semantic_retry_semantic_correct_rate"] == 0.84
    assert payload["checks"]["best_of_schema_valid_rate"] == 1.0
    assert payload["checks"]["best_of_semantic_correct_rate"] == 1.0
    assert payload["checks"]["selected_attempt_regressions"] == 0
    assert payload["checks"]["improved_rows"] > 0
    assert matrix["evidence_boundary"].startswith("Deterministic fixture retry matrix")
    assert audit["status"] == "PASS"
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "triage.json").exists()


def test_mbs_lang_matrix_reports_token_fairness_and_boundaries(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_mbs_lang_matrix.py"
    spec = importlib.util.spec_from_file_location("run_mbs_lang_matrix", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        "sys.argv",
        ["run_mbs_lang_matrix.py", "--root", str(root), "--out-dir", str(tmp_path), "--json"],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    matrix = json.loads((tmp_path / "mbs_lang_matrix.json").read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert payload["classification"] == "fixture_mbs_lang_matrix_not_provider_benchmark"
    assert payload["checks"]["languages"] == ["ar", "de", "en", "es", "fr", "hu", "tr"]
    assert payload["checks"]["domains"] == ["fintech", "procurement", "qme_source_review", "support", "tool_call_safety"]
    assert payload["checks"]["rows"] == 15
    assert payload["checks"]["case_files"] == 7
    assert payload["checks"]["contract_boundary_failures"] == 0
    assert payload["checks"]["schema_valid_rate"] == 1.0
    assert payload["checks"]["semantic_correct_rate"] == 1.0
    assert payload["checks"]["language_mismatch_rate"] == 0.0
    assert payload["checks"]["cost_per_valid_output_tokens"] is not None
    assert payload["checks"]["schema_keys_preserved"] is True
    assert payload["checks"]["enum_values_preserved"] is True
    assert matrix["evidence_boundary"].startswith("Deterministic MBS-Lang fixture matrix")
    assert all(row["token_fairness_ratio"] is not None for row in matrix["rows"])
    assert {row["domain"] for row in matrix["rows"]} == {
        "fintech",
        "procurement",
        "qme_source_review",
        "support",
        "tool_call_safety",
    }
    assert all(row["schema_valid"] is True for row in matrix["rows"])
    assert all(row["semantic_correct"] is True for row in matrix["rows"])
    assert all(row["language_mismatch"] is False for row in matrix["rows"])
    assert (tmp_path / "mbs_lang_matrix.md").exists()


def test_mbs_lang_provider_fixture_builds_classified_evidence(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "build_lang_provider_evidence.py"
    spec = importlib.util.spec_from_file_location("build_lang_provider_evidence", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_lang_provider_evidence.py",
            "--root",
            str(root),
            "--responses",
            str(root / "examples" / "multilingual_risk_review" / "provider_json_mode_good.jsonl"),
            "--out-dir",
            str(tmp_path),
            "--model",
            "fixture-lang-provider",
            "--decoding-mode",
            "json_mode",
            "--classification",
            "fixture",
            "--json",
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out)
    result = json.loads((tmp_path / "mbs_lang_provider.mbs.json").read_text(encoding="utf-8"))
    pack_manifest = json.loads((tmp_path / "evidence_pack" / "manifest.json").read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert payload["classification_label"] == "fixture_mbs_lang_not_provider_benchmark"
    assert payload["checks"]["languages"] == ["ar", "de", "en", "es", "fr", "hu", "tr"]
    assert payload["checks"]["gate_status"] == "PASS"
    assert payload["checks"]["input_language_rows_present"] is True
    assert payload["checks"]["contract_language_en"] is True
    assert result["summary"]["runs"] == 15
    assert result["summary"]["schema_valid_rate"] == 1.0
    assert result["summary"]["semantic_correct_rate"] == 1.0
    assert {row["input_language"] for row in result["rows"]} == {"ar", "de", "en", "es", "fr", "hu", "tr"}
    assert pack_manifest["classification"] == "fixture_smoke_not_provider_benchmark"


def test_mbs_lang_provider_runner_dry_run_plans_collection(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_lang_provider_evidence.py"
    spec = importlib.util.spec_from_file_location("run_lang_provider_evidence", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_lang_provider_evidence.py",
            "--root",
            str(root),
            "--out-dir",
            str(tmp_path),
            "--model",
            "provider-model",
            "--provider",
            "openai-compatible",
            "--endpoint",
            "http://127.0.0.1:8000",
            "--mode",
            "json_mode",
            "--classification",
            "oss",
            "--dry-run",
            "--json",
        ],
    )

    assert module.main() == 0
    plan = json.loads((tmp_path / "run_plan.json").read_text(encoding="utf-8"))

    assert plan["classification"] == "oss"
    assert plan["collected_responses"] is True
    assert len(plan["commands"]) == 2
    assert "collect_azure_openai_responses.py" in plan["commands"][0][1]
    assert "build_lang_provider_evidence.py" in plan["commands"][1][1]
    assert str(root / "examples" / "multilingual_risk_review" / "cases.jsonl") in plan["commands"][0]


def test_mbs_lang_provider_summary_preserves_provider_boundary():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "assert_mbs_lang_provider_summary.py"
    spec = importlib.util.spec_from_file_location("assert_mbs_lang_provider_summary", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    summary_path = root / "docs" / "mbs_lang_provider_summary_20260514" / "mbs_lang_provider_matrix.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    failures = module.validate_summary(payload)

    assert failures == []
    assert payload["classification_label"] == "real_provider_mbs_lang_behavior_evidence"
    assert payload["raw_provider_outputs_public"] is False
    assert len(payload["rows"]) == 6
    assert {row["model"] for row in payload["rows"]} == {"gpt-5-3-chat", "gpt-4-1-nano", "gpt-5-nano"}
    assert {row["decoding_mode"] for row in payload["rows"]} == {"json_mode", "tool_call"}
    assert {row["gate_status"] for row in payload["rows"]} == {"PASS", "FAIL"}
    assert all(row["case_runs"] == 7 and row["traceable_case_rows"] == 7 for row in payload["rows"])
    assert all(row["languages"] == ["ar", "de", "en", "es", "fr", "hu", "tr"] for row in payload["rows"])
    nano_rows = [row for row in payload["rows"] if row["model"] == "gpt-5-nano"]
    assert len(nano_rows) == 2
    assert all(row["top_failures"] == "invalid_json:7" for row in nano_rows)
    assert all(row["infra_failed_rows"] == 0 for row in nano_rows)


def test_mbs_lang_provider_expanded_summary_preserves_failed_gate_boundary():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "assert_mbs_lang_provider_expanded_summary.py"
    spec = importlib.util.spec_from_file_location("assert_mbs_lang_provider_expanded_summary", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    summary_path = root / "docs" / "mbs_lang_provider_expanded_summary_20260514" / "mbs_lang_provider_expanded_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    failures = module.validate_summary(payload)
    row = payload["rows"][0]

    assert failures == []
    assert payload["classification_label"] == "real_provider_mbs_lang_behavior_evidence"
    assert payload["raw_provider_outputs_public"] is False
    assert row["case_runs"] == 15
    assert row["traceable_case_rows"] == 15
    assert row["gate_status"] == "FAIL"
    assert row["primary_failure_mode"] == "provider_content_filter"
    assert row["infra_failed_rows"] == 1
    assert row["top_failures"] == "content_filter:16"


def test_mbs_lang_oss_hpc_dry_run_makes_no_model_claim():
    root = Path(__file__).resolve().parents[1]
    dry_run_path = root / "docs" / "mbs_lang_oss_hpc_endpoint_dry_run_20260514" / "endpoint_dry_run.json"
    payload = json.loads(dry_run_path.read_text(encoding="utf-8"))

    assert payload["model_behavior_evidence"] is False
    assert payload["raw_provider_outputs_public"] is False
    assert payload["planned_run"]["dry_run_only"] is True
    assert payload["planned_run"]["classification"] == "oss"
    assert payload["planned_run"]["provider"] == "openai-compatible"
    assert "no OSS/HPC model pass/fail claim" in payload["evidence_boundary"]


def test_nested_provider_runner_dry_run_plans_collection(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_nested_provider_evidence.py"
    spec = importlib.util.spec_from_file_location("run_nested_provider_evidence_dry_run", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out_dir = tmp_path / "nested_provider_dry_run"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_nested_provider_evidence.py",
            "--root",
            str(root),
            "--out-dir",
            str(out_dir),
            "--model",
            "provider-model",
            "--provider",
            "openai-compatible",
            "--endpoint",
            "http://127.0.0.1:8000",
            "--mode",
            "tool_call",
            "--classification",
            "oss",
            "--dry-run",
            "--json",
        ],
    )

    assert module.main() == 0
    plan = json.loads((out_dir / "run_plan.json").read_text(encoding="utf-8"))

    assert plan["classification"] == "oss"
    assert plan["collected_responses"] is True
    assert len(plan["commands"]) == 2
    assert "collect_azure_openai_responses.py" in plan["commands"][0][1]
    assert "build_nested_provider_evidence.py" in plan["commands"][1][1]


def test_ci_artifact_checker_accepts_complete_fixture_outputs(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    results_dir = tmp_path / "benchmarks" / "results"
    results_dir.mkdir(parents=True)
    ci_result = results_dir / "ci_bench.json"
    ci_result.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "summary": {"runs": 1, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0, "clean_json_rate": 1.0},
                "rows": [{"status": "PASS", "trace": {"trace_id": "mbs_trace_ok", "tokens": {"output": 3}}}],
            }
        ),
        encoding="utf-8",
    )
    gate_path = tmp_path / "gate.yaml"
    gate_path.write_text("thresholds:\n  min_schema_valid_rate: 1.0\n", encoding="utf-8")
    build_evidence_pack([ci_result], results_dir / "evidence_pack_ci", classification="ci", gate_config=gate_path, copy_results=True)
    (results_dir / "ci_report.md").write_text("# report\n", encoding="utf-8")
    (results_dir / "ci_gate.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    (results_dir / "ci_environment.json").write_text(
        json.dumps({"status": "PASS", "evidence_type": "ci_environment_manifest", "runner_os": "local-test"}),
        encoding="utf-8",
    )

    nested_script_path = root / "scripts" / "run_nested_tool_fixture_pack.py"
    nested_spec = importlib.util.spec_from_file_location("run_nested_tool_fixture_pack_for_ci_check", nested_script_path)
    assert nested_spec and nested_spec.loader
    nested_module = importlib.util.module_from_spec(nested_spec)
    nested_spec.loader.exec_module(nested_module)
    monkeypatch.setattr(
        "sys.argv",
        ["run_nested_tool_fixture_pack.py", "--root", str(root), "--out-dir", str(results_dir / "nested_tool_fixture_pack")],
    )
    assert nested_module.main() == 0

    multi_schema_script_path = root / "scripts" / "run_multi_schema_fixture_bundle.py"
    multi_schema_spec = importlib.util.spec_from_file_location(
        "run_multi_schema_fixture_bundle_for_ci_check", multi_schema_script_path
    )
    assert multi_schema_spec and multi_schema_spec.loader
    multi_schema_module = importlib.util.module_from_spec(multi_schema_spec)
    multi_schema_spec.loader.exec_module(multi_schema_module)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_multi_schema_fixture_bundle.py",
            "--root",
            str(root),
            "--out-dir",
            str(results_dir / "multi_schema_fixture_bundle"),
        ],
    )
    assert multi_schema_module.main() == 0

    checker_path = root / "scripts" / "assert_ci_artifacts.py"
    checker_spec = importlib.util.spec_from_file_location("assert_ci_artifacts", checker_path)
    assert checker_spec and checker_spec.loader
    checker = importlib.util.module_from_spec(checker_spec)
    checker_spec.loader.exec_module(checker)
    monkeypatch.setattr("sys.argv", ["assert_ci_artifacts.py", "--results-dir", str(results_dir), "--json"])

    assert checker.main() == 0


def test_make_response_template_cli_and_api(tmp_path, capsys):
    cases_path = tmp_path / "cases.jsonl"
    out_path = tmp_path / "template.jsonl"
    cases_path.write_text(
        json.dumps({"id": "a", "input": "case a", "expected_valid_outputs": {"decision": "REVIEW"}}) + "\n",
        encoding="utf-8",
    )

    rows = make_response_template(cases_path, output_field="tool_call", model="provider-x", decoding_mode="tool_call")
    assert rows == [
        {
            "case_id": "a",
            "input": "case a",
            "model": "provider-x",
            "decoding_mode": "tool_call",
            "tool_call": {"function": {"name": "fill_provider_tool_name", "arguments": {}}},
        }
    ]

    assert (
        main(
            [
                "make-response-template",
                "--cases",
                str(cases_path),
                "--out",
                str(out_path),
                "--output-field",
                "arguments",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    written = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert payload["rows"] == 1
    assert written == [{"case_id": "a", "input": "case a", "arguments": {}}]


def test_cli_agent_tools_lists_and_calls(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")

    assert main(["agent-tools", "--list"]) == 0
    assert "mbs.check" in capsys.readouterr().out

    args_path = tmp_path / "args.json"
    args_path.write_text(
        json.dumps(
            {
                "schema_path": str(schema_path),
                "output": {"decision": "REVIEW", "risk_level": "HIGH", "reason": "manual review"},
            }
        ),
        encoding="utf-8",
    )

    assert main(["agent-tools", "--call", "mbs.validate", "--args", str(args_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "mbs.validate"
    assert payload["result"]["status"] == "PASS"


def test_cost_accounts_for_retry_input_tokens():
    cost = report_cost(
        [
            {
                "schema_valid": True,
                "retry_count": 2,
                "tokens": {"mbs_contract": 10, "output": 5},
            }
        ]
    )

    assert cost["input_tokens"] == 30
    assert cost["output_tokens"] == 5
    assert cost["cost_per_valid_output_tokens"] == 35.0


def test_retry_prompt_uses_failure_specific_guidance():
    validation = {
        "errors": [
            {
                "field": "priority",
                "type": "invented_enum",
                "received": "high",
                "allowed": ["LOW", "MEDIUM", "HIGH"],
            }
        ]
    }

    guidance = retry_guidance(validation)
    prompt = build_retry_prompt("Return JSON.", '{"priority":"high"}', validation)

    assert any("choose exactly one allowed value" in line for line in guidance)
    assert "never join alternatives" in prompt
    assert '"received": "high"' in prompt
    assert prompt.endswith("Output the corrected raw JSON object.")


def test_retry_guidance_handles_reasoning_prose():
    guidance = retry_guidance({"errors": [{"field": "$", "type": "reasoning_prose"}]})

    assert any("chain-of-thought" in line for line in guidance)


def test_benchmark_matrix_summarizes_models_styles_and_languages(tmp_path):
    schema_path, cases_path = _write_schema_and_cases(tmp_path)

    result = run_benchmark_matrix(
        schema_path,
        cases_path,
        models=["mock", "mock_retry"],
        prompt_styles=["natural", "progressive"],
        decoding_modes=["local_mock"],
        languages=["ar"],
    )

    assert result["summary"]["matrix_runs"] == 4
    assert result["summary"]["models"] == 2
    assert result["summary"]["schema_valid_rate"] == 1.0
    assert {row["model"] for row in result["rows"]} == {"mock", "mock_retry"}
    assert all(row["language"] == "in=ar;out=ar;contract=en" for row in result["rows"])


def test_local_mock_generates_valid_strict_fintech_ci_outputs():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "examples" / "fintech_transaction_risk" / "schema.json").read_text(encoding="utf-8"))
    cases = [
        json.loads(line)
        for line in (root / "examples" / "fintech_transaction_risk" / "cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    rows = run_cases(schema, cases, model="mock", decoding_mode="local_mock")

    assert summarize(rows)["schema_valid_rate"] == 1.0
    assert summarize(rows)["semantic_correct_rate"] == 1.0
    for case in cases:
        output = mock_output(schema, case["input"])
        for key, value in case["expected_valid_outputs"].items():
            assert output[key] == value


def test_cli_bench_accepts_models_yaml(tmp_path, capsys):
    schema_path, cases_path = _write_schema_and_cases(tmp_path)
    config_path = tmp_path / "models.yaml"
    out_path = tmp_path / "bench_results" / "result.json"
    config_path.write_text(
        "\n".join(
            [
                f"schema: {schema_path}",
                f"cases: {cases_path}",
                "models:",
                "  - mock",
                "prompt_styles:",
                "  - natural",
            ]
        ),
        encoding="utf-8",
    )

    assert main(["bench", "--config", str(config_path), "--json", "--out", str(out_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["matrix_runs"] == 1
    assert payload["summary"]["schema_valid_rate"] == 1.0
    assert json.loads(out_path.read_text(encoding="utf-8"))["summary"]["matrix_runs"] == 1


def test_demo_is_small_and_traceable():
    demo = build_demo()

    assert demo["check"]["status"] == "FAIL"
    assert demo["check"]["failure_type"] == "invalid_enum"
    assert demo["check"]["trace_id"].startswith("mbs_trace_")
    assert demo["retry"]["status"] == "PASS"
    assert demo["contract"]["mbs_tokens"] < demo["contract"]["verbose_tokens"]
    assert demo["cost"]["cost_per_valid_output_tokens"] is not None


def test_demo_benchmark_compares_two_models_and_three_cases():
    benchmark = run_sample_benchmark()
    rows = benchmark["summary"]["by_strategy"]
    by_strategy = {row["strategy"]: row for row in rows}

    assert benchmark["cases"] == 3
    assert len(benchmark["models"]) == 2
    assert by_strategy["verbose_prompt"]["cases"] == 6
    assert by_strategy["mbs_contract+retry"]["cases"] == 6
    assert by_strategy["mbs_contract+retry"]["schema_valid_rate"] > by_strategy["verbose_prompt"]["schema_valid_rate"]
    assert by_strategy["mbs_contract+retry"]["semantic_correct_rate"] > by_strategy["verbose_prompt"]["semantic_correct_rate"]


def test_cli_demo_prints_and_writes_artifacts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert main(["demo", "--write-artifacts"]) == 0
    output = capsys.readouterr().out

    assert "MBS Demo" in output
    assert "Sample benchmark:" in output
    assert (tmp_path / "benchmarks" / "results" / "sample_benchmark.json").exists()
    assert (tmp_path / "benchmarks" / "results" / "sample_benchmark.md").exists()
    assert (tmp_path / "docs" / "mbs_evidence_brief.md").exists()


def test_cli_test_uses_models_config(tmp_path, capsys):
    schema_path, cases_path = _write_schema_and_cases(tmp_path)
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "risk_schema.json").write_text(schema_path.read_text(encoding="utf-8"), encoding="utf-8")
    models_path = tmp_path / "models.yaml"
    models_path.write_text("models:\n  - mock\n  - mock_second\n", encoding="utf-8")

    assert main(["test", "--schemas", str(schemas_dir), "--cases", str(cases_path), "--models", str(models_path)]) == 0
    output = capsys.readouterr().out
    assert "[mock]" in output
    assert "[mock_second]" in output


def test_compile_language_contract_includes_language_wrapper():
    result = compile_language_contract(SCHEMA, input_language="ar", output_language="ar", contract_language="en")

    assert "Analyze ar input." in result["prompt"]
    assert "Use ar for free-text explanation fields." in result["prompt"]
    assert result["token_fairness_ratio"] is not None
    assert result["english_baseline_tokens"] > 0


def test_report_aggregates_benchmark_results(tmp_path):
    result_path = tmp_path / "bench.json"
    result_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "schema": "schema.json",
                        "model": "mock",
                        "prompt_style": "natural",
                        "decoding_mode": "local_mock",
                        "language": "default",
                        "runs": 2,
                        "schema_valid_rate": 1.0,
                        "semantic_correct_rate": 0.5,
                        "failure_types": {"semantic_mismatch": 1},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = aggregate_results([result_path])
    markdown = markdown_report(report)

    assert report["summary"]["rows"] == 1
    assert report["summary"]["total_runs"] == 2
    assert "semantic_mismatch" in markdown


def test_report_scorecards_rank_models_and_failures(tmp_path):
    result_path = tmp_path / "bench.json"
    result_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "schema": "schema.json",
                        "model": "strong-model",
                        "prompt_style": "full",
                        "language": "in=en;out=en;contract=en",
                        "runs": 4,
                        "avg_retry_count": 0.0,
                        "valid_json_rate": 1.0,
                        "clean_json_rate": 1.0,
                        "schema_valid_rate": 1.0,
                        "semantic_correct_rate": 0.9,
                    },
                    {
                        "schema": "schema.json",
                        "model": "weak-model",
                        "prompt_style": "natural",
                        "language": "in=ar;out=en;contract=en",
                        "runs": 2,
                        "avg_retry_count": 1.0,
                        "valid_json_rate": 0.5,
                        "clean_json_rate": 0.0,
                        "schema_valid_rate": 0.25,
                        "semantic_correct_rate": 0.0,
                        "failure_types": {"invalid_json": 1, "invented_enum": 1},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = aggregate_results([result_path])
    markdown = markdown_report(report, summary_only=True)

    assert report["model_scorecards"][0]["model"] == "strong-model"
    assert report["model_scorecards"][0]["status"] == "PASS"
    assert report["model_scorecards"][0]["clean_json_rate"] == 1.0
    assert report["model_scorecards"][-1]["status"] == "FAIL"
    assert report["model_scorecards"][-1]["clean_json_rate"] == 0.0
    assert report["model_scorecards"][-1]["avg_retry_count"] == 1.0
    assert report["dimension_scorecards"]["language"][0]["value"] == "in=en;out=en;contract=en"
    assert report["dimension_scorecards"]["prompt_style"][0]["value"] == "full"
    assert report["failure_summary"] == [
        {"failure_type": "invalid_json", "count": 1},
        {"failure_type": "invented_enum", "count": 1},
    ]
    assert "## Model Scorecard" in markdown
    assert "## Language Scorecard" in markdown
    assert "## Prompt Style Scorecard" in markdown
    assert "## Failure Summary" in markdown
    assert "Mean clean-JSON rate" in markdown
    assert "| schema | model |" not in markdown


def test_report_scorecards_label_format_risk(tmp_path):
    result_path = tmp_path / "bench.json"
    result_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "schema": "schema.json",
                        "model": "wrapped-json-model",
                        "prompt_style": "full",
                        "runs": 4,
                        "valid_json_rate": 1.0,
                        "clean_json_rate": 0.0,
                        "schema_valid_rate": 1.0,
                        "semantic_correct_rate": 1.0,
                        "failure_types": {"prose_wrapped_json": 4},
                    },
                    {
                        "schema": "schema.json",
                        "model": "reasoning-model",
                        "prompt_style": "full",
                        "runs": 4,
                        "valid_json_rate": 0.25,
                        "clean_json_rate": 0.0,
                        "schema_valid_rate": 0.9,
                        "semantic_correct_rate": 0.8,
                        "failure_types": {"reasoning_prose": 3},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = aggregate_results([result_path])
    cards = {row["model"]: row for row in report["model_scorecards"]}
    markdown = markdown_report(report, summary_only=True)

    assert cards["wrapped-json-model"]["status"] == "REVIEW"
    assert cards["wrapped-json-model"]["format_risk"] == "prose_wrapped_json"
    assert cards["reasoning-model"]["status"] == "FAIL"
    assert cards["reasoning-model"]["format_risk"] == "reasoning_prose"
    assert "format_risk" in markdown


def test_report_can_exclude_infra_failures(tmp_path):
    good_path = tmp_path / "good.json"
    infra_path = tmp_path / "infra.json"
    good_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock-good",
                "prompt_style": "full",
                "summary": {"runs": 2, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0},
                "rows": [{"status": "PASS", "trace": {"trace_id": "t", "tokens": {"output": 1}}}],
            }
        ),
        encoding="utf-8",
    )
    infra_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock-missing",
                "prompt_style": "full",
                "infra_failure": "model_load_failed",
                "summary": {"runs": 1, "schema_valid_rate": 0.0, "failure_types": {"model_load_failed": 1}},
                "rows": [{"status": "INFRA_FAIL", "failure_type": "model_load_failed"}],
            }
        ),
        encoding="utf-8",
    )

    report = aggregate_results([good_path, infra_path], exclude_infra=True)
    markdown = markdown_report(report)

    assert report["summary"]["input_rows"] == 2
    assert report["summary"]["rows"] == 1
    assert report["summary"]["infra_failed_rows"] == 1
    assert report["summary"]["mean_behavior_schema_valid_rate"] == 1.0
    assert report["rows"][0]["model"] == "mock-good"
    assert "Infra-failed rows: 1" in markdown
    assert "mock-missing" not in markdown


def test_report_uses_single_benchmark_metadata(tmp_path):
    result_path = tmp_path / "single.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "examples/schema.json",
                "model": "mock",
                "prompt_style": "natural",
                "decoding_mode": "local_mock",
                "language": "default",
                "summary": {"runs": 3, "schema_valid_rate": 0.3333},
            }
        ),
        encoding="utf-8",
    )

    report = aggregate_results([result_path])

    assert report["rows"][0]["schema"] == "examples/schema.json"
    assert report["rows"][0]["model"] == "mock"
    assert report["rows"][0]["prompt_style"] == "natural"


def test_cli_report_writes_markdown(tmp_path, capsys):
    result_path = tmp_path / "bench.json"
    out_path = tmp_path / "report.md"
    result_path.write_text(
        json.dumps({"runs": [{"schema": "schema.json", "model": "mock", "runs": 1, "schema_valid_rate": 1.0}]}),
        encoding="utf-8",
    )

    assert main(["report", "--results", str(result_path), "--out", str(out_path)]) == 0
    output = capsys.readouterr().out
    assert "MBS Benchmark Report" in output
    assert "| schema | model |" in out_path.read_text(encoding="utf-8")


def test_cli_report_exclude_infra_filters_table(tmp_path, capsys):
    result_path = tmp_path / "bench.json"
    result_path.write_text(
        json.dumps(
            {
                "runs": [
                    {"schema": "schema.json", "model": "mock-good", "runs": 1, "schema_valid_rate": 1.0},
                    {
                        "schema": "schema.json",
                        "model": "mock-missing",
                        "runs": 1,
                        "schema_valid_rate": 0.0,
                        "infra_failure": "model_load_failed",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    assert main(["report", "--results", str(result_path), "--exclude-infra"]) == 0
    output = capsys.readouterr().out
    assert "mock-good" in output
    assert "mock-missing" not in output
    assert "Infra-failed rows: 1" in output


def test_cli_report_require_traces_blocks_untraceable_rows(tmp_path, capsys):
    result_path = tmp_path / "bench.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "summary": {"runs": 2, "schema_valid_rate": 1.0},
                "rows": [
                    {"status": "PASS", "trace": {"trace_id": "mbs_trace_ok", "tokens": {"output": 3}}},
                    {"status": "PASS", "trace": {}},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["report", "--results", str(result_path), "--require-traces"]) == 2
    output = capsys.readouterr().out
    assert "Traceable case rows: 1" in output
    assert "Missing trace rows: 1" in output
    assert "Trace check failed" in output


def test_gate_passes_clean_traceable_results(tmp_path):
    result_path = tmp_path / "bench.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "summary": {"runs": 1, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0, "clean_json_rate": 1.0},
                "rows": [{"status": "PASS", "trace": {"trace_id": "mbs_trace_ok", "tokens": {"output": 3}}}],
            }
        ),
        encoding="utf-8",
    )
    config = {"thresholds": {"min_schema_valid_rate": 1.0, "min_semantic_correct_rate": 1.0, "min_clean_json_rate": 1.0}}

    result = evaluate_gate([result_path], config=config)

    assert result["status"] == "PASS"
    assert not result["failures"]
    assert "All configured thresholds passed" in format_gate(result)


def test_gate_and_report_fail_empty_result_sets(tmp_path, capsys):
    empty_path = tmp_path / "empty.json"
    empty_path.write_text(json.dumps({"summary": {"runs": 0}, "rows": []}), encoding="utf-8")

    gate = evaluate_gate([empty_path])
    gate_metrics = {failure["metric"] for failure in gate["failures"]}

    assert gate["status"] == "FAIL"
    assert gate["failure_reason"].startswith("gate_failed:")
    assert "rows" in gate_metrics
    assert "total_runs" in gate_metrics
    assert main(["gate", "--results", str(empty_path), "--json"]) == 2
    gate_payload = json.loads(capsys.readouterr().out)
    assert gate_payload["status"] == "FAIL"
    assert gate_payload["failure_reason"]

    assert main(["report", "--results", str(empty_path), "--json"]) == 2
    report_payload = json.loads(capsys.readouterr().out)
    assert report_payload["summary"]["rows"] == 0


def test_gate_fails_bad_metrics_and_missing_traces(tmp_path):
    result_path = tmp_path / "bench.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "summary": {"runs": 2, "schema_valid_rate": 0.5, "semantic_correct_rate": 0.5, "clean_json_rate": 0.5},
                "rows": [
                    {"status": "PASS", "trace": {"trace_id": "mbs_trace_ok", "tokens": {"output": 3}}},
                    {"status": "FAIL", "trace": {}},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = evaluate_gate([result_path], config={"thresholds": {"min_schema_valid_rate": 0.9}})
    failed_metrics = {failure["metric"] for failure in result["failures"]}

    assert result["status"] == "FAIL"
    assert result["failure_reason"].startswith("gate_failed:")
    assert "mean_schema_valid_rate" in failed_metrics
    assert "missing_trace_rows" in failed_metrics
    assert "trace_coverage" in failed_metrics


def test_gate_enforces_provider_coverage_thresholds(tmp_path):
    result_path = tmp_path / "provider.json"
    result_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "schema": "schema-a.json",
                        "model": "provider-model-a",
                        "runs": 2,
                        "schema_valid_rate": 1.0,
                        "semantic_correct_rate": 1.0,
                        "clean_json_rate": 1.0,
                    }
                ],
                "rows": [
                    {
                        "schema": "schema-a.json",
                        "model": "provider-model-a",
                        "status": "PASS",
                        "schema_valid": True,
                        "semantic_correct": True,
                        "trace": {"trace_id": "mbs_trace_1", "tokens": {"output": 3}},
                    },
                    {
                        "schema": "schema-a.json",
                        "model": "provider-model-a",
                        "status": "PASS",
                        "schema_valid": True,
                        "semantic_correct": True,
                        "trace": {"trace_id": "mbs_trace_2", "tokens": {"output": 3}},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    config = {"thresholds": {"min_rows": 2, "min_total_runs": 4, "min_models": 2, "min_schemas": 2}}

    result = evaluate_gate([result_path], config=config)
    failed_metrics = {failure["metric"] for failure in result["failures"]}

    assert result["status"] == "FAIL"
    assert {"total_runs", "models", "schemas"} <= failed_metrics


def test_cli_gate_uses_yaml_config_and_writes_json(tmp_path, capsys):
    result_path = tmp_path / "bench.json"
    config_path = tmp_path / "gate.yaml"
    out_path = tmp_path / "gate.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "summary": {"runs": 1, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0, "clean_json_rate": 1.0},
                "rows": [{"status": "PASS", "trace": {"trace_id": "mbs_trace_ok", "tokens": {"output": 3}}}],
            }
        ),
        encoding="utf-8",
    )
    config_path.write_text("thresholds:\n  min_schema_valid_rate: 1.0\n  min_semantic_correct_rate: 1.0\n", encoding="utf-8")

    assert main(["gate", "--results", str(result_path), "--config", str(config_path), "--out", str(out_path)]) == 0
    written = json.loads(out_path.read_text(encoding="utf-8"))

    assert "Status: PASS" in capsys.readouterr().out
    assert load_gate_config(config_path)["thresholds"]["min_schema_valid_rate"] == 1.0
    assert written["status"] == "PASS"


def test_evidence_pack_writes_reviewable_artifacts(tmp_path):
    result_path = tmp_path / "bench.json"
    gate_path = tmp_path / "gate.yaml"
    out_dir = tmp_path / "pack"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "summary": {"runs": 1, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0, "clean_json_rate": 1.0},
                "rows": [{"status": "PASS", "trace": {"trace_id": "mbs_trace_ok", "tokens": {"output": 3}}}],
            }
        ),
        encoding="utf-8",
    )
    gate_path.write_text("thresholds:\n  min_schema_valid_rate: 1.0\n", encoding="utf-8")

    manifest = build_evidence_pack(
        [result_path],
        out_dir,
        classification="ci",
        gate_config=gate_path,
        copy_results=True,
    )

    assert manifest["classification"] == "ci_regression_check_not_broad_model_benchmark"
    assert manifest["checks"]["gate_status"] == "PASS"
    assert (out_dir / "README.md").exists()
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "gate.json").exists()
    assert (out_dir / "triage.md").exists()
    assert (out_dir / "raw_results" / "bench.json").exists()
    assert "not broad model benchmark evidence" in (out_dir / "README.md").read_text(encoding="utf-8")


def test_cli_evidence_pack_returns_nonzero_when_gate_fails(tmp_path, capsys):
    result_path = tmp_path / "bench.json"
    gate_path = tmp_path / "gate.yaml"
    out_dir = tmp_path / "pack"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "summary": {"runs": 1, "schema_valid_rate": 0.5, "semantic_correct_rate": 0.5, "clean_json_rate": 0.5},
                "rows": [{"status": "FAIL", "trace": {"trace_id": "mbs_trace_bad", "tokens": {"output": 3}}}],
            }
        ),
        encoding="utf-8",
    )
    gate_path.write_text("thresholds:\n  min_schema_valid_rate: 1.0\n", encoding="utf-8")

    assert (
        main(
            [
                "evidence-pack",
                "--results",
                str(result_path),
                "--gate-config",
                str(gate_path),
                "--classification",
                "provider",
                "--out-dir",
                str(out_dir),
            ]
        )
        == 2
    )
    output = capsys.readouterr().out
    assert "Gate status: FAIL" in output
    assert json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))["classification"] == "real_provider_behavior_evidence"


def test_cli_validate_bad_inline_json_reports_invalid_json(tmp_path, capsys):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")

    assert main(["validate", "--schema", str(schema_path), "--output", "{bad json", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["errors"][0]["type"] == "invalid_json"


def test_compare_results_detects_regression(tmp_path):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    row = {
        "schema": "schema.json",
        "model": "mock",
        "prompt_style": "natural",
        "decoding_mode": "local_mock",
        "language": "default",
        "runs": 2,
    }
    baseline.write_text(json.dumps({"runs": [{**row, "schema_valid_rate": 1.0, "enum_accuracy": 1.0}]}), encoding="utf-8")
    current.write_text(json.dumps({"runs": [{**row, "schema_valid_rate": 0.5, "enum_accuracy": 0.5}]}), encoding="utf-8")

    result = compare_results([baseline], [current])

    assert result["status"] == "FAIL"
    assert {item["metric"] for item in result["regressions"]} == {"schema_valid_rate", "enum_accuracy"}
    assert "Regression detected" in format_compare(result)


def test_cli_compare_returns_nonzero_on_regression(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(json.dumps({"runs": [{"schema": "schema.json", "model": "mock", "schema_valid_rate": 1.0}]}), encoding="utf-8")
    current.write_text(json.dumps({"runs": [{"schema": "schema.json", "model": "mock", "schema_valid_rate": 0.0}]}), encoding="utf-8")

    assert main(["compare", "--baseline", str(baseline), "--current", str(current), "--metric", "schema_valid_rate"]) == 2
    assert "Regression detected" in capsys.readouterr().out


def test_compare_no_match_is_nonpassing_with_reason(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps({"runs": [{"schema": "schema-a.json", "model": "mock-a", "schema_valid_rate": 1.0}]}),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps({"runs": [{"schema": "schema-b.json", "model": "mock-b", "schema_valid_rate": 1.0}]}),
        encoding="utf-8",
    )

    result = compare_results([baseline], [current])

    assert result["status"] == "NO_MATCH"
    assert result["reason"] == "no comparable metric rows matched between baseline and current results"
    assert result["comparisons"] == []
    assert "No comparable rows matched" in format_compare(result)

    assert main(["compare", "--baseline", str(baseline), "--current", str(current), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "NO_MATCH"
    assert payload["reason"]


def test_retry_audit_passes_when_selected_attempt_improves(tmp_path):
    result_path = tmp_path / "retry.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "prompt_style": "full",
                "language": "default",
                "rows": [
                    {
                        "case_id": "case_1",
                        "retry_count": 1,
                        "attempts": [
                            {
                                "attempt": 0,
                                "json_valid": False,
                                "schema_valid": False,
                                "semantic_correct": False,
                                "failure_type": "invalid_json",
                                "selected": False,
                            },
                            {
                                "attempt": 1,
                                "json_valid": True,
                                "schema_valid": True,
                                "semantic_correct": True,
                                "failure_type": None,
                                "selected": True,
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = audit_retry_attempts([result_path])

    assert result["status"] == "PASS"
    assert result["audited_rows"] == 1
    assert result["improved_rows"] == 1
    assert "Selected attempt regressions: 0" in format_retry_audit(result)


def test_cli_retry_audit_fails_when_selected_attempt_regresses(tmp_path, capsys):
    result_path = tmp_path / "retry.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "schema.json",
                "model": "mock",
                "rows": [
                    {
                        "case_id": "case_1",
                        "retry_count": 1,
                        "attempts": [
                            {
                                "attempt": 0,
                                "json_valid": True,
                                "schema_valid": True,
                                "semantic_correct": True,
                                "selected": False,
                            },
                            {
                                "attempt": 1,
                                "json_valid": True,
                                "schema_valid": False,
                                "semantic_correct": False,
                                "failure_type": "invented_enum",
                                "selected": True,
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["retry-audit", "--results", str(result_path)]) == 2
    output = capsys.readouterr().out
    assert "Selected attempt regressions: 1" in output


def test_model_suite_has_broad_coverage():
    registry = load_model_registry("benchmarks/model_suites.json")
    models = suite_models(registry, "stage1_broad")
    summary = suite_summary(models)

    assert summary["models"] >= 30
    assert summary["families"] >= 10
    assert len(summary["size_bands"]) >= 3
    assert not validate_suite_coverage(models, min_models=30, min_families=10, min_size_bands=3)


def test_cli_models_exports_model_list(tmp_path, capsys):
    out = tmp_path / "models.txt"

    assert (
        main(
            [
                "models",
                "--suite",
                "stage1_broad",
                "--min-models",
                "30",
                "--min-families",
                "10",
                "--min-size-bands",
                "3",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert len([line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]) >= 30
    assert "Families:" in capsys.readouterr().out


def test_triage_flags_missing_models_and_failures(tmp_path):
    result_path = tmp_path / "result.json"
    expected_path = tmp_path / "models.txt"
    expected_path.write_text("mock\nmissing-model\n", encoding="utf-8")
    result_path.write_text(
        json.dumps(
            {
                "model": "mock",
                "summary": {
                    "runs": 1,
                    "valid_json_rate": 1.0,
                    "schema_valid_rate": 0.5,
                    "failure_types": {"invented_enum": 1},
                },
                "rows": [{"trace": {"trace_id": "mbs_trace_test", "tokens": {"mbs_contract": 1, "output": 1}}}],
            }
        ),
        encoding="utf-8",
    )

    result = triage_results([result_path], expected_models=expected_path)

    assert result["status"] == "FAIL"
    assert "missing-model" in result["missing_models"]
    assert result["issue_summary"]["missing_model_result"] == 1
    assert {issue["type"] for issue in result["issues"]} >= {
        "missing_model_result",
        "low_schema_valid_rate",
        "failure_types_present",
    }


def test_triage_exports_case_level_failure_examples(tmp_path):
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema": "examples/tool_argument_generation/schema.json",
                "model": "mock",
                "prompt_style": "natural",
                "language": "default",
                "summary": {
                    "runs": 1,
                    "valid_json_rate": 1.0,
                    "schema_valid_rate": 0.0,
                    "failure_types": {"invented_enum": 1},
                },
                "rows": [
                    {
                        "case_id": "tool_001",
                        "model": "mock",
                        "status": "FAIL",
                        "schema_valid": False,
                        "semantic_correct": False,
                        "failure_type": "invented_enum",
                        "errors": [{"field": "priority", "type": "invented_enum", "received": "high"}],
                        "trace": {"trace_id": "mbs_trace_case", "tokens": {"output": 1}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = triage_results([result_path], max_failure_examples=5)

    assert result["failure_examples"] == [
        {
            "failure_type": "invented_enum",
            "case_id": "tool_001",
            "model": "mock",
            "schema": "examples/tool_argument_generation/schema.json",
            "prompt_style": "natural",
            "language": "default",
            "status": "FAIL",
            "trace_id": "mbs_trace_case",
            "detail": "priority; invented_enum; received=high",
            "source": "result.json",
        }
    ]


def test_cli_triage_reports_failures(tmp_path, capsys):
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "model": "mock",
                "summary": {"schema_valid_rate": 0.0},
                "rows": [
                    {
                        "case_id": "case_001",
                        "status": "FAIL",
                        "schema_valid": False,
                        "failure_type": "invalid_json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["triage", "--results", str(result_path)]) == 2
    output = capsys.readouterr().out
    assert "Issue summary:" in output
    assert "Issues shown:" in output
    assert "Failure examples:" in output


def test_triage_handles_test_summary_list(tmp_path):
    result_path = tmp_path / "test_rows.json"
    expected_path = tmp_path / "models.txt"
    expected_path.write_text("mock\n", encoding="utf-8")
    result_path.write_text(
        json.dumps([{"schema": "schema.json", "model": "mock", "runs": 1, "schema_valid_rate": 1.0, "valid_json_rate": 1.0}]),
        encoding="utf-8",
    )

    result = triage_results([result_path], expected_models=expected_path, require_traces=False)

    assert result["status"] == "PASS"
    assert result["observed_models"] == ["mock"]


def test_triage_reads_tsv_model_lists(tmp_path):
    result_path = tmp_path / "result.json"
    expected_path = tmp_path / "models.tsv"
    expected_path.write_text("mock\t/local/model/path\n", encoding="utf-8")
    result_path.write_text(
        json.dumps(
            {
                "model": "mock",
                "summary": {"schema_valid_rate": 1.0, "valid_json_rate": 1.0},
                "rows": [{"trace": {"trace_id": "mbs_trace_test", "tokens": {"output": 1}}}],
            }
        ),
        encoding="utf-8",
    )

    result = triage_results([result_path], expected_models=expected_path)

    assert result["status"] == "PASS"
    assert result["expected_models"] == ["mock"]
    assert result["missing_models"] == []


def _write_schema_and_cases(tmp_path: Path) -> tuple[Path, Path]:
    schema_path = tmp_path / "schema.json"
    cases_path = tmp_path / "cases.jsonl"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    cases_path.write_text(
        json.dumps(
            {
                "id": "case_001",
                "input": "Customer sends a high-risk transfer",
                "expected_valid_outputs": ["REVIEW", "BLOCK"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return schema_path, cases_path
