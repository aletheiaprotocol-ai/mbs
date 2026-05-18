import json
from types import SimpleNamespace
from pathlib import Path

from scripts import crosscheck_leonardo_hpc_artifacts as crosscheck
from scripts import leonardo_mbs_hf_matrix as runner
from scripts import summarize_leonardo_hpc_artifacts as summarize


def test_leonardo_crosscheck_loads_runner_contract():
    schema, cases = crosscheck._load_runner_contract()

    assert schema["type"] == "object"
    assert set(schema["properties"]) == {"tool", "priority", "customer", "actions", "reason"}
    assert len(cases) >= 8
    assert {"id", "input", "expected_valid_outputs"}.issubset(cases[0])


def test_leonardo_runner_compact_prompt_requests_json_only():
    case = json.loads(runner.CASES_JSONL.splitlines()[0])

    prompt = runner.build_prompt(case, "compact")

    assert "Return JSON only" in prompt
    assert "tool, priority, customer, actions, reason" in prompt
    assert case["input"] in prompt


def test_leonardo_parse_jsonish_distinguishes_clean_and_embedded_json():
    clean_payload = '{"tool":"request_info","priority":"LOW","customer":{"id":"x","verified":false},"actions":[],"reason":"need id"}'
    embedded_payload = f"Here is the answer: {clean_payload}"

    clean_obj, clean = runner.parse_jsonish(clean_payload)
    embedded_obj, embedded_clean = runner.parse_jsonish(embedded_payload)

    assert clean is True
    assert embedded_clean is False
    assert clean_obj == embedded_obj


def test_leonardo_result_payload_requires_clean_json_for_gate_pass():
    cases = [json.loads(line) for line in runner.CASES_JSONL.splitlines()[:8]]
    checks = [
        runner.RowResult(valid_json=True, schema_valid=True, semantic_correct=True, clean_json=False, failure_reason=None, output={})
        for _ in cases
    ]
    rows = [{"mbs_check": runner.row_check_payload(check, case)} for check, case in zip(checks, cases)]

    payload = runner.result_payload("test-model", cases, rows, checks, infra_failures=0, load_error=None)

    assert payload["summary"]["schema_valid_rate"] == 1.0
    assert payload["summary"]["semantic_correct_rate"] == 1.0
    assert payload["summary"]["clean_json_rate"] == 0.0
    assert payload["summary"]["gate_status"] == "FAIL"


def test_leonardo_crosscheck_read_json_accepts_utf8_sig(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("\ufeff" + json.dumps({"model": "m"}), encoding="utf-8")

    assert crosscheck._read_json(path) == {"model": "m"}


def test_leonardo_crosscheck_record_includes_prompt_result_metrics(tmp_path):
    model_dir = tmp_path / "suite" / "Model"
    standard_dir = model_dir / "standard_mbs"
    standard_dir.mkdir(parents=True)
    (model_dir / "manifest.json").write_text(json.dumps({"model": "org/model"}), encoding="utf-8")
    result_path = standard_dir / "result.json"
    result_path.write_text(
        json.dumps({"summary": {"runs": 8, "schema_valid_rate": 1.0, "semantic_correct_rate": 0.5, "clean_json_rate": 0.0}}),
        encoding="utf-8",
    )
    (standard_dir / "gate.json").write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")

    record = crosscheck._record(model_dir, result_path, skipped=False)

    assert record["model"] == "org/model"
    assert record["suite"] == "suite"
    assert record["gate_status"] == "FAIL"
    assert record["runs"] == 8
    assert record["schema_valid_rate"] == 1.0


def test_leonardo_crosscheck_main_accepts_explicit_summary_out(monkeypatch, tmp_path):
    root = tmp_path / "mirror"
    model_dir = root / "suite" / "Model"
    model_dir.mkdir(parents=True)
    responses = model_dir / "responses.jsonl"
    responses.write_text(json.dumps({"case_id": "nested_001", "response": "{}"}) + "\n", encoding="utf-8")
    (model_dir / "manifest.json").write_text(json.dumps({"model": "org/model"}), encoding="utf-8")

    def fake_load_runner_contract():
        return {"type": "object"}, [{"id": "nested_001", "input": "x", "expected_valid_outputs": [{}]}]

    def fake_adapt_response_jsonl(*args, **kwargs):
        return {"summary": {"runs": 1, "schema_valid_rate": 1.0, "semantic_correct_rate": 1.0, "clean_json_rate": 1.0}, "rows": []}

    monkeypatch.setattr(crosscheck, "_load_runner_contract", fake_load_runner_contract)
    monkeypatch.setattr(crosscheck, "adapt_response_jsonl", fake_adapt_response_jsonl)
    monkeypatch.setattr(crosscheck, "aggregate_results", lambda paths, exclude_infra=False: {"summary": {"runs": len(paths)}})
    monkeypatch.setattr(crosscheck, "evaluate_gate", lambda paths, exclude_infra=False: {"status": "PASS"})
    monkeypatch.setattr(crosscheck, "write_gate_json", lambda path, gate: path.write_text(json.dumps(gate), encoding="utf-8"))
    out_path = tmp_path / "custom" / "summary.json"

    rc = crosscheck.main(["--root", str(root), "--out", str(out_path)])

    summary = json.loads(out_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert summary["root"] == str(root)
    assert summary["processed_count"] == 1
    assert (model_dir / "standard_mbs" / "result.json").exists()


def test_leonardo_summarizer_skips_standard_mbs_and_preserves_prompt_style(tmp_path):
    root = tmp_path / "mirror"
    model_dir = root / "compact_best_01_41807858" / "Qwen_Qwen2.5-14B-Instruct"
    model_dir.mkdir(parents=True)
    (model_dir / "manifest.json").write_text(
        json.dumps(
            {
                "model": "Qwen/Qwen2.5-14B-Instruct",
                "suite": "medium",
                "prompt_style": "compact",
                "status": "FAIL",
                "classification": "hpc_model_behavior_evidence",
                "checks": {
                    "runs": 8,
                    "behavior_runs": 8,
                    "infra_failed_rows": 0,
                    "schema_valid_rate": 1.0,
                    "semantic_correct_rate": 0.75,
                    "clean_json_rate": 1.0,
                    "gate_status": "FAIL",
                },
            }
        ),
        encoding="utf-8",
    )
    derived_dir = model_dir / "standard_mbs"
    derived_dir.mkdir()
    (derived_dir / "manifest.json").write_text(json.dumps({"model": "derived"}), encoding="utf-8")

    summary = summarize.summarize(root)

    assert summary["count"] == 1
    row = summary["rows"][0]
    assert row["run"] == "compact_best_01_41807858"
    assert row["prompt_style"] == "compact"
    assert row["model"] == "Qwen/Qwen2.5-14B-Instruct"


def test_leonardo_summarizer_counts_multiple_model_manifests_once(tmp_path):
    root = tmp_path / "mirror"
    for model_dir, model in [
        ("Qwen_Qwen2.5-14B-Instruct", "Qwen/Qwen2.5-14B-Instruct"),
        ("01-ai_Yi-1.5-9B-Chat", "01-ai/Yi-1.5-9B-Chat"),
    ]:
        target = root / "compact_best_01_41807858" / model_dir
        target.mkdir(parents=True)
        (target / "manifest.json").write_text(
            json.dumps(
                {
                    "model": model,
                    "suite": "large",
                    "status": "FAIL",
                    "classification": "hpc_model_behavior_evidence",
                    "checks": {"runs": 12, "behavior_runs": 12, "infra_failed_rows": 0, "gate_status": "FAIL"},
                }
            ),
            encoding="utf-8",
        )
        derived = target / "standard_mbs"
        derived.mkdir()
        (derived / "manifest.json").write_text(json.dumps({"model": "derived"}), encoding="utf-8")

    summary = summarize.summarize(root)

    assert summary["count"] == 2
    assert {row["model"] for row in summary["rows"]} == {"Qwen/Qwen2.5-14B-Instruct", "01-ai/Yi-1.5-9B-Chat"}
    assert all(row["run"] == "compact_best_01_41807858" for row in summary["rows"])


def test_leonardo_main_matrix_manifest_includes_prompt_style(monkeypatch, tmp_path):
    def fake_run_model(model_id, cases, args, out_dir):
        return {"model": model_id, "prompt_style": args.prompt_style, "checks": {}}

    monkeypatch.setattr(runner, "run_model", fake_run_model)
    out_dir = tmp_path / "out"

    rc = runner.main([
        "--suite",
        "smoke",
        "--models",
        "test/model",
        "--out-dir",
        str(out_dir),
        "--limit",
        "1",
        "--prompt-style",
        "compact",
    ])

    matrix = json.loads((out_dir / "matrix_manifest.json").read_text(encoding="utf-8"))
    assert rc == 0
    assert matrix["prompt_style"] == "compact"
    assert matrix["manifests"][0]["prompt_style"] == "compact"