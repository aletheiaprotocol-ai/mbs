"""Validate the active hard nested tool-argument suite and fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_IDS = {f"nested_{idx:03d}" for idx in range(1, 26)}
REQUIRED_TEXT_SNIPPETS = [
    "two duplicate",
    "disallowed",
    "unsupported",
    "negative",
    "0 GBP",
    "no source",
    "stale source",
    "ignore all previous rules",
    "fake source",
    "ambiguous",
    "Partially verified",
    "human review",
    "retry instruction",
]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def validate_suite(root: Path) -> dict[str, Any]:
    example_dir = root / "examples" / "nested_tool_arguments"
    cases_path = example_dir / "cases.jsonl"
    good_path = example_dir / "provider_tool_call_good.jsonl"
    bad_path = example_dir / "provider_tool_call_bad.jsonl"
    archived_path = example_dir / "cases_8_may2026.jsonl"

    cases = _load_jsonl(cases_path)
    good = _load_jsonl(good_path)
    bad = _load_jsonl(bad_path)
    archived = _load_jsonl(archived_path)
    failures: list[str] = []

    case_ids = {str(case.get("id")) for case in cases}
    good_ids = {str(row.get("case_id")) for row in good}
    bad_ids = {str(row.get("case_id")) for row in bad}
    archived_ids = {str(case.get("id")) for case in archived}

    if len(cases) != 25 or case_ids != REQUIRED_IDS:
        failures.append("active cases.jsonl must contain exactly nested_001..nested_025")
    if good_ids != case_ids:
        failures.append("good fixture rows must exactly match active case ids")
    if bad_ids != case_ids:
        failures.append("bad fixture rows must exactly match active case ids")
    if len(archived) != 8 or archived_ids != {f"nested_{idx:03d}" for idx in range(1, 9)}:
        failures.append("cases_8_may2026.jsonl must preserve the original eight Azure matrix cases")

    combined_inputs = "\n".join(str(case.get("input", "")) for case in cases)
    for snippet in REQUIRED_TEXT_SNIPPETS:
        if snippet not in combined_inputs:
            failures.append(f"expanded suite missing expected trap text: {snippet}")

    for case in cases:
        expected = case.get("expected_valid_outputs")
        if not isinstance(expected, dict) or "tool" not in expected or "priority" not in expected:
            failures.append(f"{case.get('id')} must declare expected tool and priority")

    return {
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "case_count": len(cases),
        "good_rows": len(good),
        "bad_rows": len(bad),
        "archived_case_count": len(archived),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    result = validate_suite(Path(args.root).resolve())
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Nested tool suite: {result['status']} ({result['case_count']} cases)")
        for failure in result["failures"]:
            print(f"- {failure}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
