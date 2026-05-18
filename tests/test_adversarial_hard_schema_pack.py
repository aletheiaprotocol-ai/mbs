import json
import subprocess
import sys
from pathlib import Path

from mbs.adapter import adapt_response_jsonl


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "adversarial_policy_execution"
SCHEMA = EXAMPLE_DIR / "schema.json"
CASES = EXAMPLE_DIR / "cases.jsonl"
GOOD_RESPONSES = EXAMPLE_DIR / "provider_good_responses.jsonl"
BAD_RESPONSES = EXAMPLE_DIR / "provider_bad_responses.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_adversarial_policy_pack_has_strict_schema_and_case_breadth():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    cases = _read_jsonl(CASES)

    assert schema["additionalProperties"] is False
    assert schema["properties"]["policy_version"]["const"] == "ape-v1"
    assert schema["properties"]["allowed_actions"]["maxItems"] == 3
    assert schema["properties"]["blocked_actions"]["items"]["additionalProperties"] is False
    assert len(cases) == 8

    combined_inputs = "\n".join(case["input"].lower() for case in cases)
    for phrase in [
        "personal address",
        "ignore all previous instructions",
        "reveal the secret token",
        "run shell",
        "lacks approval chain",
        "disable mfa",
        "drop tables",
        "request more identity information",
    ]:
        assert phrase in combined_inputs


def test_adversarial_policy_good_and_bad_fixtures_exercise_hard_schema():
    good = adapt_response_jsonl(
        SCHEMA,
        GOOD_RESPONSES,
        cases_path=CASES,
        model="adversarial-good-fixture",
        decoding_mode="json_mode",
    )
    bad = adapt_response_jsonl(
        SCHEMA,
        BAD_RESPONSES,
        cases_path=CASES,
        model="adversarial-bad-fixture",
        decoding_mode="json_mode",
    )

    assert good["summary"]["runs"] == 8
    assert good["summary"]["schema_valid_rate"] == 1.0
    assert good["summary"]["semantic_correct_rate"] == 1.0
    assert bad["summary"]["runs"] == 8
    assert bad["summary"]["schema_valid_rate"] < 0.25
    assert bad["summary"]["semantic_correct_rate"] < 0.25
    assert sum(1 for row in bad["rows"] if row["status"] in {"FAIL", "REVIEW"}) == 8

    failure_types = {
        str(error.get("type"))
        for row in bad["rows"]
        for error in [*(row.get("errors") or []), *(row.get("warnings") or [])]
    }
    assert {
        "invalid_enum",
        "invented_enum",
        "above_maximum",
        "wrong_type",
        "const_mismatch",
        "extra_key",
        "too_few_items",
        "pattern_mismatch",
        "missing_required_key",
        "safety_review_required",
    } <= failure_types


def test_adversarial_hard_schema_runner_builds_b004_manifest(tmp_path):
    out_dir = tmp_path / "adversarial_hard_schema_pack"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_adversarial_hard_schema_pack.py",
            "--out-dir",
            str(out_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["blocker"] == "B-004"
    assert manifest["classification"] == "fixture_adversarial_not_provider_benchmark"
    assert manifest["evidence_boundary"]["not_provider_benchmark"] is True
    assert manifest["checks"]["good_runs"] == 8
    assert manifest["checks"]["bad_runs"] == 8
    assert manifest["checks"]["bad_fail_or_review_rows"] == 8
    assert manifest["checks"]["traceable_case_rows"] == 16
    assert manifest["checks"]["missing_trace_rows"] == 0
    assert manifest["checks"]["missing_expected_failures"] == {}
    assert (out_dir / "evidence_pack" / "report.md").exists()
    assert (out_dir / "README.md").exists()
