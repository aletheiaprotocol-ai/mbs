import json
from pathlib import Path

from mbs import call_agent_tool, check, handle_agent_tool_request, list_agent_tools, report_cost, validate_output
from mbs.adapter import adapt_response_jsonl, make_response_template
from mbs.bench import run_benchmark_matrix
from mbs.cli import main
from mbs.compare import compare_results, format_compare
from mbs.demo import build_demo, run_sample_benchmark
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

    assert response["tool"] == "mbs.validate"
    assert response["result"]["schema_valid"] is False
    assert response["result"]["errors"][0]["type"] == "invented_enum"


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
