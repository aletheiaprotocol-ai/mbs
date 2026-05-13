import json

from scripts.analyze_mbs_failures import analyze, expand_paths, load_cases, markdown_report


def test_analyze_mbs_failures_separates_infra_and_behavior(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "input": "suspicious login",
                "expected_valid_outputs": {"action": "ESCALATE_SECURITY", "priority": "CRITICAL"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result_path = tmp_path / "provider.mbs.json"
    result_path.write_text(
        json.dumps(
            {
                "model": "unit-model",
                "decoding_mode": "json_mode",
                "rows": [
                    {
                        "case_id": "case-1",
                        "model": "unit-model",
                        "decoding_mode": "json_mode",
                        "status": "FAIL",
                        "json_valid": True,
                        "schema_valid": True,
                        "semantic_correct": False,
                        "failure_type": "semantic_mismatch",
                    },
                    {
                        "case_id": "infra",
                        "model": "unit-model",
                        "decoding_mode": "json_mode",
                        "status": "INFRA_FAIL",
                        "infra_failure": "DeploymentNotFound",
                        "json_valid": False,
                        "schema_valid": False,
                        "semantic_correct": False,
                        "failure_type": "DeploymentNotFound",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    responses_path = tmp_path / "provider.responses.jsonl"
    responses_path.write_text(
        json.dumps(
            {
                "case_id": "case-1",
                "response": '{"action":"CREATE_TICKET","priority":"HIGH"}',
            }
        )
        + "\n",
        encoding="utf-8",
    )

    analysis = analyze([result_path], cases=load_cases(str(cases_path)), exclude_infra=True)

    assert analysis["input_rows"] == 2
    assert analysis["behavior_rows"] == 1
    assert analysis["infra_failed_rows"] == 1
    assert analysis["failure_types"] == {"semantic_mismatch": 1}
    assert analysis["models"][0]["semantic_correct_rate"] == 0.0
    assert analysis["cases"][0]["observed_actions"] == {"CREATE_TICKET": 1}


def test_expand_paths_and_markdown_report(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    result_path = nested / "sample.mbs.json"
    result_path.write_text('{"model":"m","rows":[]}', encoding="utf-8")

    paths = expand_paths([str(tmp_path)])
    report = markdown_report(
        {
            "files": [str(result_path)],
            "input_rows": 0,
            "behavior_rows": 0,
            "infra_failed_rows": 0,
            "models": [],
            "cases": [],
            "failure_types": {},
        }
    )

    assert paths == [result_path.resolve()]
    assert "# MBS Failure Analysis" in report
    assert "Behavior rows: 0" in report