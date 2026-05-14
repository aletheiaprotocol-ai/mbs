import json
from pathlib import Path


SUMMARY_DIR = Path("docs/provider_matrix_summary_20260514")
SUMMARY_JSON = SUMMARY_DIR / "provider_matrix_summary.json"
SUMMARY_README = SUMMARY_DIR / "README.md"


def _load_summary():
    return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))


def test_provider_matrix_summary_preserves_failed_gates():
    summary = _load_summary()

    assert summary["classification"] == "provider"
    assert summary["classification_label"] == "real_provider_behavior_evidence_sanitized_summary"
    assert summary["raw_artifacts_public"] is False
    assert summary["case_count"] == 8
    assert summary["cases"].endswith("cases_8_may2026.jsonl")
    assert summary["active_suite_cases"].endswith("cases.jsonl")

    rows = summary["rows"]
    assert {row["deployment"] for row in rows} == {"gpt-5-3-chat", "gpt-5-nano", "gpt-4-1-nano"}
    assert all(row["gate_status"] == "FAIL" for row in rows)
    assert all(row["infra_failed_rows"] == 0 for row in rows)
    assert all(row["traceable_case_rows"] == summary["case_count"] for row in rows)


def test_provider_matrix_summary_preserves_distinct_failure_modes():
    rows = {row["deployment"]: row for row in _load_summary()["rows"]}

    assert rows["gpt-5-3-chat"]["primary_failure_mode"] == "schema_clean_semantic_mismatch"
    assert rows["gpt-5-3-chat"]["schema_valid_rate"] == 1.0
    assert rows["gpt-5-3-chat"]["semantic_correct_rate"] == 0.625

    assert rows["gpt-4-1-nano"]["primary_failure_mode"] == "schema_clean_semantic_mismatch"
    assert rows["gpt-4-1-nano"]["schema_valid_rate"] == 1.0
    assert rows["gpt-4-1-nano"]["semantic_correct_rate"] == 0.375

    assert rows["gpt-5-nano"]["primary_failure_mode"] == "format_schema_failure"
    assert rows["gpt-5-nano"]["schema_valid_rate"] == 0.0
    assert rows["gpt-5-nano"]["clean_json_rate"] == 0.0


def test_provider_matrix_summary_readme_declares_non_claims():
    readme = SUMMARY_README.read_text(encoding="utf-8")

    assert "does not claim broad provider reliability" in readme
    assert "does not claim any listed deployment passed" in readme
    assert "does not publish raw provider responses" in readme
    assert "does not mix fixture evidence with provider behavior evidence" in readme
