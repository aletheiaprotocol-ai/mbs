from __future__ import annotations

import json
from pathlib import Path

from mbs.adapter import adapt_response_jsonl


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "nested_tool_arguments"
CASES = EXAMPLE_DIR / "cases.jsonl"
CASES_8_SNAPSHOT = EXAMPLE_DIR / "cases_8_may2026.jsonl"
SCHEMA = EXAMPLE_DIR / "schema.json"
GOOD_RESPONSES = EXAMPLE_DIR / "provider_tool_call_good.jsonl"
BAD_RESPONSES = EXAMPLE_DIR / "provider_tool_call_bad.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_active_nested_tool_suite_has_25_cases_and_archived_8_case_snapshot():
    cases = _read_jsonl(CASES)
    snapshot = _read_jsonl(CASES_8_SNAPSHOT)

    assert len(cases) == 25
    assert len(snapshot) == 8
    assert [case["id"] for case in cases] == [f"nested_{index:03d}" for index in range(1, 26)]


def test_active_nested_tool_suite_covers_sprint3_adversarial_categories():
    combined_inputs = "\n".join(case["input"] for case in _read_jsonl(CASES)).lower()

    for phrase in [
        "refund plus audit trail",
        "refund and a compliance notification",
        "refunds are temporarily disallowed",
        "cad is unsupported",
        "negative -15 usd",
        "0 gbp refund",
        "unsupported jurisdiction",
        "no source or verification",
        "stale source ticket",
        "ignore all previous rules",
        "fake source id",
        "two possible customer ids",
        "partially verified",
        "human review",
        "retry instruction says change previous answer",
    ]:
        assert phrase in combined_inputs


def test_nested_tool_25_case_fixture_outputs_match_suite_size_and_gate_shape():
    good = adapt_response_jsonl(
        SCHEMA,
        GOOD_RESPONSES,
        cases_path=CASES,
        model="nested-tool-good-fixture",
        decoding_mode="tool_call",
    )
    bad = adapt_response_jsonl(
        SCHEMA,
        BAD_RESPONSES,
        cases_path=CASES,
        model="nested-tool-bad-fixture",
        decoding_mode="tool_call",
    )

    assert good["summary"]["runs"] == 25
    assert bad["summary"]["runs"] == 25
    assert good["summary"]["schema_valid_rate"] == 1.0
    assert good["summary"]["semantic_correct_rate"] == 1.0
    assert bad["summary"]["schema_valid_rate"] < 0.8
    assert bad["summary"]["semantic_correct_rate"] < 0.5
