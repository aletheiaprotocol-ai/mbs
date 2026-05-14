"""Validate the public OSS/HPC endpoint dry-run no-evidence record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FORBIDDEN_EVIDENCE_FLAGS = {
    "raw_responses_collected": False,
    "evidence_pack_created": False,
    "aggregate_matrix_row_created": False,
}


def validate_record(path: Path) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []

    if record.get("status") != "NO_EVIDENCE_DRY_RUN":
        failures.append("status must be NO_EVIDENCE_DRY_RUN")
    if record.get("classification") not in {"oss", "hpc"}:
        failures.append("classification must be oss or hpc")

    probe = record.get("endpoint_probe", {})
    checked_urls = probe.get("checked_urls", [])
    if len(checked_urls) < 3:
        failures.append("record must include at least three checked endpoint URLs")
    if probe.get("reachable_endpoints"):
        failures.append("reachable_endpoints must be empty for a no-evidence record")

    boundary = record.get("evidence_boundary", {})
    for key, expected in FORBIDDEN_EVIDENCE_FLAGS.items():
        if boundary.get(key) is not expected:
            failures.append(f"evidence_boundary.{key} must be {expected}")

    dry_run_plan = record.get("dry_run_plan", {})
    if dry_run_plan.get("classification") != record.get("classification"):
        failures.append("dry_run_plan classification must match record classification")
    if not dry_run_plan.get("would_collect_responses"):
        failures.append("dry_run_plan must describe response collection for real runs")
    if not dry_run_plan.get("would_build_evidence_pack"):
        failures.append("dry_run_plan must describe evidence-pack creation for real runs")

    non_claims = "\n".join(record.get("non_claims", []))
    for required in ["not an OSS benchmark", "not an HPC benchmark", "does not contain raw model outputs"]:
        if required not in non_claims:
            failures.append(f"missing non-claim: {required}")

    return {"status": "FAIL" if failures else "PASS", "failures": failures, "checked_urls": len(checked_urls)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record",
        default="docs/oss_hpc_endpoint_dry_run_20260514/endpoint_dry_run.json",
        help="Path to the OSS/HPC dry-run record JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    result = validate_record(Path(args.record))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"OSS/HPC dry-run record: {result['status']} ({result['checked_urls']} checked URLs)")
        for failure in result["failures"]:
            print(f"- {failure}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
