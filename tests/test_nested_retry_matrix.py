from __future__ import annotations

import json
from pathlib import Path

from scripts.run_nested_retry_matrix import main as run_nested_retry_matrix


def test_nested_retry_matrix_outputs_required_strategies_and_metrics(tmp_path):
    out_dir = tmp_path / "nested_retry_matrix"

    assert run_nested_retry_matrix(["--out-dir", str(out_dir)]) == 0

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    matrix = json.loads((out_dir / "retry_matrix_summary.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "PASS"
    assert manifest["classification"] == "fixture_retry_matrix_not_provider_benchmark"
    assert manifest["checks"]["case_count"] == 25
    assert manifest["checks"]["strategies"] == [
        "no_retry",
        "mbs_retry",
        "format_retry",
        "semantic_retry",
        "best_of_retry",
    ]
    assert manifest["checks"]["selected_attempt_regressions"] == 0
    assert manifest["checks"]["improved_rows"] > 0

    strategies = matrix["strategies"]
    assert strategies["no_retry"]["summary"]["semantic_correct_rate"] == 0.2
    assert strategies["format_retry"]["summary"]["schema_valid_rate"] == 1.0
    assert strategies["semantic_retry"]["summary"]["semantic_correct_rate"] == 0.84
    assert strategies["mbs_retry"]["summary"]["semantic_correct_rate"] == 1.0
    assert strategies["best_of_retry"]["summary"]["semantic_correct_rate"] == 1.0

    for strategy in manifest["checks"]["strategies"]:
        metrics = strategies[strategy]["policy_metrics"]
        assert "improved_rows" in metrics
        assert "unchanged_rows" in metrics
        assert "selected_attempt_regressions" in metrics
        assert "clean_json_rate" in metrics
        assert "cost_per_valid_output_tokens" in metrics


def test_nested_retry_matrix_writes_report_audit_and_triage(tmp_path):
    out_dir = tmp_path / "nested_retry_matrix"

    assert run_nested_retry_matrix(["--out-dir", str(out_dir)]) == 0

    for relative in [
        "report.md",
        "retry_audit.json",
        "retry_audit.md",
        "triage.json",
        "no_retry.mbs.json",
        "mbs_retry.mbs.json",
        "format_retry.mbs.json",
        "semantic_retry.mbs.json",
        "best_of_retry.mbs.json",
    ]:
        assert (out_dir / relative).exists()

    audit = json.loads((out_dir / "retry_audit.json").read_text(encoding="utf-8"))
    assert audit["status"] == "PASS"
    assert audit["selected_attempt_regressions"] == 0
