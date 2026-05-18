"""Build B-004 hard-schema adversarial fixture evidence.

This runner is local software/fixture evidence. It proves a strict schema accepts
known-good outputs and catches deliberately bad outputs across enum drift,
additional properties, bounds, patterns, missing required keys, type mismatches,
and schema-valid unsafe text warnings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mbs.adapter import adapt_response_jsonl
from mbs.evidence import build_evidence_pack
from mbs.report import aggregate_results


EXAMPLE_DIR = Path("examples/adversarial_policy_execution")
EXPECTED_BAD_FAILURE_TYPES = {
    "adv_001": {"invalid_enum"},
    "adv_002": {"invented_enum", "above_maximum", "wrong_type"},
    "adv_003": {"const_mismatch", "extra_key"},
    "adv_004": {"invalid_enum", "too_few_items"},
    "adv_005": {"pattern_mismatch"},
    "adv_006": {"missing_required_key"},
    "adv_007": {"pattern_mismatch"},
    "adv_008": {"safety_review_required"},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build B-004 adversarial hard-schema evidence")
    parser.add_argument("--root", default=".", help="MBS repo root")
    parser.add_argument("--out-dir", default="benchmarks/results/adversarial_hard_schema_pack")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    results_dir = out_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    schema = root / EXAMPLE_DIR / "schema.json"
    cases = root / EXAMPLE_DIR / "cases.jsonl"
    good_responses = root / EXAMPLE_DIR / "provider_good_responses.jsonl"
    bad_responses = root / EXAMPLE_DIR / "provider_bad_responses.jsonl"

    good_payload = adapt_response_jsonl(
        schema,
        good_responses,
        cases_path=cases,
        model="adversarial-policy-good-fixture",
        decoding_mode="json_mode",
    )
    bad_payload = adapt_response_jsonl(
        schema,
        bad_responses,
        cases_path=cases,
        model="adversarial-policy-bad-fixture",
        decoding_mode="json_mode",
    )

    good_path = results_dir / "adversarial_policy_execution.good.mbs.json"
    bad_path = results_dir / "adversarial_policy_execution.bad.mbs.json"
    _write_json(good_path, good_payload)
    _write_json(bad_path, bad_payload)

    report = aggregate_results([good_path, bad_path])
    pack_manifest = build_evidence_pack(
        [good_path, bad_path],
        out_dir / "evidence_pack",
        classification="fixture",
        copy_results=True,
        title="MBS B-004 Adversarial Hard-Schema Pack",
    )

    bad_rows = {str(row["case_id"]): row for row in bad_payload["rows"]}
    failure_matrix = {
        case_id: sorted(_row_failure_types(row)) for case_id, row in sorted(bad_rows.items())
    }
    missing_expected_failures = {
        case_id: sorted(expected - set(failure_matrix.get(case_id, [])))
        for case_id, expected in EXPECTED_BAD_FAILURE_TYPES.items()
        if expected - set(failure_matrix.get(case_id, []))
    }

    warning_rows = [row for row in bad_payload["rows"] if row["status"] == "REVIEW"]
    checks = {
        "good_runs": good_payload["summary"].get("runs"),
        "bad_runs": bad_payload["summary"].get("runs"),
        "good_schema_valid_rate": good_payload["summary"].get("schema_valid_rate"),
        "good_semantic_correct_rate": good_payload["summary"].get("semantic_correct_rate"),
        "bad_schema_valid_rate": bad_payload["summary"].get("schema_valid_rate"),
        "bad_semantic_correct_rate": bad_payload["summary"].get("semantic_correct_rate"),
        "bad_fail_or_review_rows": sum(1 for row in bad_payload["rows"] if row["status"] in {"FAIL", "REVIEW"}),
        "warning_review_rows": len(warning_rows),
        "traceable_case_rows": report["summary"].get("traceable_case_rows"),
        "missing_trace_rows": report["summary"].get("missing_trace_rows"),
        "total_runs": report["summary"].get("total_runs"),
        "missing_expected_failures": missing_expected_failures,
        "evidence_pack_files": pack_manifest["checks"].get("result_files"),
    }
    passed = (
        checks["good_runs"] == 8
        and checks["bad_runs"] == 8
        and checks["good_schema_valid_rate"] == 1.0
        and checks["good_semantic_correct_rate"] == 1.0
        and checks["bad_schema_valid_rate"] < 0.25
        and checks["bad_semantic_correct_rate"] < 0.25
        and checks["bad_fail_or_review_rows"] == 8
        and checks["warning_review_rows"] >= 1
        and checks["traceable_case_rows"] == 16
        and checks["missing_trace_rows"] == 0
        and checks["total_runs"] == 16
        and checks["missing_expected_failures"] == {}
    )

    manifest = {
        "status": "PASS" if passed else "FAIL",
        "blocker": "B-004",
        "purpose": "hard-schema adversarial fixture evidence",
        "classification": "fixture_adversarial_not_provider_benchmark",
        "evidence_boundary": {
            "not_provider_benchmark": True,
            "not_remote_ci_evidence": True,
            "public_claim_boundary": "Local strict-schema adversarial software fixtures only.",
        },
        "schema": str(EXAMPLE_DIR / "schema.json"),
        "cases": str(EXAMPLE_DIR / "cases.jsonl"),
        "artifacts": {
            "results_dir": str(results_dir),
            "good_results": str(good_path),
            "bad_results": str(bad_path),
            "evidence_pack": str(out_dir / "evidence_pack"),
            "manifest": str(out_dir / "manifest.json"),
        },
        "checks": checks,
        "failure_matrix": failure_matrix,
        "remaining_boundary": "Provider/OSS breadth, real provider-classified workflow runs, remote CI, and governance review remain separate blockers.",
    }
    _write_json(out_dir / "manifest.json", manifest)
    (out_dir / "README.md").write_text(_readme(manifest), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"MBS adversarial hard-schema pack: {manifest['status']}")
        print(f"Good runs: {checks['good_runs']}")
        print(f"Bad runs: {checks['bad_runs']}")
        print(f"Bad fail/review rows: {checks['bad_fail_or_review_rows']}")
        print(f"Missing expected failures: {checks['missing_expected_failures']}")
        print(f"Manifest: {out_dir / 'manifest.json'}")
    return 0 if passed else 2


def _row_failure_types(row: dict[str, Any]) -> set[str]:
    failure_types = {str(error.get("type")) for error in row.get("errors") or []}
    failure_types.update(str(warning.get("type")) for warning in row.get("warnings") or [])
    if row.get("failure_type"):
        failure_types.add(str(row["failure_type"]))
    return {item for item in failure_types if item and item != "None"}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _readme(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    lines = [
        "# MBS B-004 Adversarial Hard-Schema Pack",
        "",
        f"Status: `{manifest['status']}`",
        f"Classification: `{manifest['classification']}`",
        "",
        "This is local strict-schema adversarial fixture evidence. It is not provider evidence and not remote CI evidence.",
        "",
        "## Checks",
        "",
        f"- Good runs: {checks['good_runs']}",
        f"- Bad runs: {checks['bad_runs']}",
        f"- Good schema-valid rate: {checks['good_schema_valid_rate']}",
        f"- Good semantic-correct rate: {checks['good_semantic_correct_rate']}",
        f"- Bad schema-valid rate: {checks['bad_schema_valid_rate']}",
        f"- Bad semantic-correct rate: {checks['bad_semantic_correct_rate']}",
        f"- Bad fail/review rows: {checks['bad_fail_or_review_rows']}",
        f"- Warning/review rows: {checks['warning_review_rows']}",
        f"- Traceable case rows: {checks['traceable_case_rows']}",
        f"- Missing trace rows: {checks['missing_trace_rows']}",
        "",
        "## Failure matrix",
        "",
    ]
    for case_id, failure_types in manifest["failure_matrix"].items():
        lines.append(f"- `{case_id}`: {', '.join(failure_types)}")
    lines.extend(["", f"Remaining boundary: {manifest['remaining_boundary']}", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
