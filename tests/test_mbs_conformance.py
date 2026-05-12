import json

import pytest

from mbs import call_agent_tool, handle_agent_tool_request
from mbs.agent_tools import AgentToolError
from mbs.bench import run_benchmark, run_benchmark_matrix, summarize
from mbs.cli import main
from mbs.compiler import compile_schema, load_schema, schema_hash
from mbs.cost import report_cost
from mbs.report import aggregate_results, expand_paths
from mbs.trace import create_trace
from mbs.validate import validate_output


NESTED_SCHEMA = {
    "type": "object",
    "properties": {
        "ticket_id": {"type": "string"},
        "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "approved": {"type": "boolean"},
        "score": {"type": "number"},
        "count": {"type": "integer"},
        "nullable_note": {"type": ["string", "null"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "qty": {"type": "integer"},
                },
                "required": ["name", "qty"],
            },
        },
    },
    "required": ["ticket_id", "priority", "approved", "score", "count", "items"],
}


VALID_OUTPUT = {
    "ticket_id": "T-001",
    "priority": "HIGH",
    "approved": False,
    "score": 0.75,
    "count": 2,
    "nullable_note": None,
    "items": [{"name": "gpu", "qty": 1}],
}


def test_compile_contract_formats_have_hashes_and_strict_boundaries():
    hashes = set()
    for fmt in ["natural", "progressive", "full", "strict"]:
        result = compile_schema(NESTED_SCHEMA, format=fmt, task_context="Classify the ticket.")
        hashes.add(result["contract_hash"])
        assert result["schema_hash"] == schema_hash(NESTED_SCHEMA)
        assert result["token_estimate"] > 0
        assert result["full_token_estimate"] > 0
        assert "priority" in result["prompt"]

    strict = compile_schema(NESTED_SCHEMA, format="strict")
    assert "first generated character {" in strict["prompt"]
    assert "chain-of-thought" in strict["prompt"]
    assert len(hashes) == 4


def test_load_schema_supports_pydantic_v2_and_v1_style_models():
    class V2Model:
        @classmethod
        def model_json_schema(cls):
            return NESTED_SCHEMA

    class V1Model:
        @classmethod
        def schema(cls):
            return {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}

    assert load_schema(V2Model)["properties"]["priority"]["enum"] == ["LOW", "MEDIUM", "HIGH"]
    assert load_schema(V1Model)["required"] == ["ok"]


def test_validate_rejects_bool_as_integer_and_number():
    integer_result = validate_output(
        {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]},
        {"count": True},
    )
    number_result = validate_output(
        {"type": "object", "properties": {"score": {"type": "number"}}, "required": ["score"]},
        {"score": False},
    )

    assert integer_result["schema_valid"] is False
    assert integer_result["errors"][0]["type"] == "wrong_type"
    assert number_result["schema_valid"] is False
    assert number_result["errors"][0]["type"] == "wrong_type"


def test_validate_nested_object_array_missing_keys_are_precise():
    result = validate_output(
        NESTED_SCHEMA,
        {
            "ticket_id": "T-002",
            "priority": "HIGH",
            "approved": True,
            "score": 1.0,
            "count": 1,
            "items": [{"name": "gpu"}],
        },
    )

    assert result["schema_valid"] is False
    assert {"field": "items[0].qty", "type": "missing_required_key"} in result["errors"]


def test_trace_hashes_are_stable_but_trace_ids_are_unique():
    contract = compile_schema(NESTED_SCHEMA, format="full")
    validation = validate_output(NESTED_SCHEMA, VALID_OUTPUT)

    first = create_trace(NESTED_SCHEMA, contract, validation, input_text="same", model="model-a", output_tokens=9)
    second = create_trace(NESTED_SCHEMA, contract, validation, input_text="same", model="model-a", output_tokens=9)

    assert first["trace_id"] != second["trace_id"]
    for key in ["schema_hash", "contract_hash", "input_hash", "output_hash"]:
        assert first[key] == second[key]
        assert first[key].startswith("sha256:")
    assert first["tokens"]["output"] == 9


def test_cost_handles_zero_valid_outputs_and_explicit_input_total():
    result = report_cost(
        [
            {"schema_valid": False, "tokens": {"input_total": 100, "output": 25}},
            {"status": "FAIL", "tokens": {"mbs_contract": 10, "output": 5}},
        ]
    )

    assert result["valid_outputs"] == 0
    assert result["failed_outputs"] == 2
    assert result["input_tokens"] == 110
    assert result["output_tokens"] == 30
    assert result["cost_per_valid_output_tokens"] is None


def test_benchmark_summary_counts_clean_json_and_warnings():
    rows = [
        {"json_valid": True, "schema_valid": True, "semantic_correct": True, "warnings": [], "errors": [], "tokens": {"output": 1}},
        {
            "json_valid": True,
            "schema_valid": True,
            "semantic_correct": False,
            "warnings": [{"type": "prose_wrapped_json"}],
            "errors": [],
            "tokens": {"output": 1},
        },
        {
            "json_valid": False,
            "schema_valid": False,
            "semantic_correct": False,
            "failure_type": "invalid_json",
            "warnings": [],
            "errors": [{"type": "invalid_json"}],
            "tokens": {"output": 1},
        },
    ]

    result = summarize(rows)

    assert result["runs"] == 3
    assert result["valid_json_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert result["clean_json_rate"] == pytest.approx(1 / 3, rel=1e-3)
    assert result["failure_types"] == {"invalid_json": 1}


def test_report_expands_result_directory_to_json_files(tmp_path):
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    payload = {
        "schema": "schema-a",
        "model": "model-a",
        "summary": {"runs": 1, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0, "clean_json_rate": 1.0},
        "rows": [{"case_id": "ok", "status": "PASS", "schema_valid": True, "semantic_correct": True, "json_valid": True}],
    }
    (result_dir / "one.json").write_text(json.dumps(payload), encoding="utf-8")
    (result_dir / "notes.txt").write_text("not a result", encoding="utf-8")

    files = expand_paths([result_dir])
    report = aggregate_results([result_dir])

    assert files == [(result_dir / "one.json").resolve()]
    assert report["summary"]["rows"] == 1
    assert report["summary"]["infra_failed_rows"] == 0


def test_run_benchmark_matrix_supports_multiple_schemas_and_language_dict(tmp_path):
    schema_a = tmp_path / "schema_a.json"
    schema_b = tmp_path / "schema_b.json"
    cases = tmp_path / "cases.jsonl"
    schema_a.write_text(json.dumps(NESTED_SCHEMA), encoding="utf-8")
    schema_b.write_text(json.dumps(NESTED_SCHEMA), encoding="utf-8")
    cases.write_text(json.dumps({"id": "case", "input": "urgent high ticket", "expected_valid_outputs": ["HIGH"]}) + "\n", encoding="utf-8")

    result = run_benchmark_matrix(
        [schema_a, schema_b],
        cases,
        models=["mock-a", "mock-b"],
        prompt_styles=["strict"],
        decoding_modes=["local_mock"],
        languages=[{"input_language": "ar", "output_language": "ar", "contract_language": "en"}],
    )

    assert result["summary"]["matrix_runs"] == 4
    assert result["summary"]["schemas"] == 2
    assert result["summary"]["models"] == 2
    assert all(row["language"] == "in=ar;out=ar;contract=en" for row in result["rows"])


def test_agent_tool_errors_are_explicit():
    with pytest.raises(AgentToolError, match="Unknown MBS agent tool"):
        call_agent_tool("mbs.unknown", {})

    with pytest.raises(AgentToolError, match="requires a string tool/name"):
        handle_agent_tool_request({"arguments": {}})

    with pytest.raises(AgentToolError, match="schema must be a JSON object"):
        call_agent_tool("mbs.validate", {"schema": "not-object", "output": {}})


def test_agent_tool_trace_and_cost_are_transport_neutral():
    trace = call_agent_tool(
        "mbs.trace",
        {"schema": NESTED_SCHEMA, "output": VALID_OUTPUT, "input": "same", "model": "agent-runtime"},
    )
    cost = call_agent_tool(
        "mbs.cost",
        {"records": [{"status": trace["status"], "tokens": trace["tokens"]}]},
    )

    assert trace["status"] == "PASS"
    assert trace["model"] == "agent-runtime"
    assert trace["tokens"]["output"] > 0
    assert cost["valid_outputs"] == 1
    assert cost["cost_per_valid_output_tokens"] is not None


def test_cli_agent_tools_request_file_and_invalid_call(tmp_path, capsys):
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps({"tool": "mbs.validate", "arguments": {"schema": NESTED_SCHEMA, "output": VALID_OUTPUT}}),
        encoding="utf-8",
    )

    assert main(["agent-tools", "--request", str(request_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["status"] == "PASS"

    with pytest.raises(SystemExit) as excinfo:
        main(["agent-tools", "--call", "mbs.unknown", "--args", "{}"])
    assert "Unknown MBS agent tool" in str(excinfo.value)


def test_cli_test_threshold_fails_low_schema_valid_rate(tmp_path):
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    schema_path = schemas / "schema.json"
    cases_path = tmp_path / "cases.jsonl"
    schema_path.write_text(json.dumps(NESTED_SCHEMA), encoding="utf-8")
    cases_path.write_text(
        json.dumps({"id": "bad", "input": "anything", "output": {"ticket_id": "T"}}) + "\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "test",
                "--schemas",
                str(schemas),
                "--cases",
                str(cases_path),
                "--min-schema-valid-rate",
                "1.0",
                "--json",
            ]
        )
        == 2
    )


def test_validate_inline_string_output_that_is_not_json_fails_cleanly():
    result = validate_output(NESTED_SCHEMA, "not json")

    assert result["json_valid"] is False
    assert result["schema_valid"] is False
    assert result["status"] == "FAIL"
    assert result["errors"][0]["type"] == "invalid_json"


def test_run_benchmark_preserves_case_ids_and_failure_types(tmp_path):
    schema_path = tmp_path / "schema.json"
    cases_path = tmp_path / "cases.jsonl"
    schema_path.write_text(json.dumps(NESTED_SCHEMA), encoding="utf-8")
    cases_path.write_text(
        "\n".join(
            [
                json.dumps({"id": "valid", "input": "high", "output": VALID_OUTPUT}),
                json.dumps({"id": "bad_enum", "input": "bad", "output": {**VALID_OUTPUT, "priority": "URGENT"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_benchmark(schema_path, cases_path, model="mock-conformance")

    assert [row["case_id"] for row in result["rows"]] == ["valid", "bad_enum"]
    assert result["rows"][0]["status"] == "PASS"
    assert result["rows"][1]["failure_type"] == "invented_enum"
    assert result["summary"]["schema_valid_rate"] == 0.5
