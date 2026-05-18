"""Assert downloaded remote CI matrix evidence is complete.

This script does not call GitHub or require credentials. It validates artifacts
after a maintainer downloads the GitHub Actions artifact bundle for the MBS CI
matrix. Passing this check is evidence that remote Ubuntu, Windows, and macOS CI
runs produced the expected reviewable MBS artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_OSES = ("ubuntu-latest", "windows-latest", "macos-latest")
REQUIRED_FILES = (
    "ci_bench.json",
    "ci_report.md",
    "ci_gate.json",
    "ci_environment.json",
    "evidence_pack_ci/manifest.json",
    "nested_tool_fixture_pack/manifest.json",
    "multi_schema_fixture_bundle/manifest.json",
)


def inspect_remote_ci_artifacts(artifacts_dir: Path) -> dict[str, Any]:
    rows = []
    for os_name in REQUIRED_OSES:
        candidates = [
            artifacts_dir / f"mbs-ci-artifacts-{os_name}-py3.11",
            artifacts_dir / os_name,
        ]
        root = next((path for path in candidates if path.exists()), candidates[0])
        missing = [name for name in REQUIRED_FILES if not (root / name).exists()]
        gate = _read_json(root / "ci_gate.json")
        evidence_manifest = _read_json(root / "evidence_pack_ci" / "manifest.json")
        environment_manifest = _read_json(root / "ci_environment.json")
        nested_manifest = _read_json(root / "nested_tool_fixture_pack" / "manifest.json")
        multi_manifest = _read_json(root / "multi_schema_fixture_bundle" / "manifest.json")
        row = {
            "os": os_name,
            "artifact_root": str(root),
            "missing_files": missing,
            "ci_gate_status": gate.get("status"),
            "evidence_pack_gate_status": evidence_manifest.get("checks", {}).get("gate_status"),
            "ci_environment_status": environment_manifest.get("status"),
            "ci_environment_type": environment_manifest.get("evidence_type"),
            "ci_runner_os": environment_manifest.get("runner_os"),
            "nested_fixture_status": nested_manifest.get("status"),
            "multi_schema_status": multi_manifest.get("status"),
        }
        row["status"] = "PASS" if _row_passes(row) else "FAIL"
        rows.append(row)

    status = "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL"
    return {
        "status": status,
        "evidence_type": "remote_ci_matrix_execution",
        "required_os": list(REQUIRED_OSES),
        "required_files_per_os": list(REQUIRED_FILES),
        "rows": rows,
        "remaining_boundary": (
            "This validates downloaded remote CI artifacts only. It does not trigger GitHub Actions, "
            "prove branch protection, or replace provider/model behavior evidence."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assert remote MBS CI matrix artifact evidence")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("benchmarks/results/remote_ci_artifacts"))
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON summary output path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = inspect_remote_ci_artifacts(args.artifacts_dir)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Remote CI matrix evidence: {result['status']}")
        for row in result["rows"]:
            print(f"- {row['os']}: {row['status']} ({row['artifact_root']})")
            for missing in row["missing_files"]:
                print(f"  missing: {missing}")
    return 0 if result["status"] == "PASS" else 2


def _row_passes(row: dict[str, Any]) -> bool:
    return (
        row["missing_files"] == []
        and row["ci_gate_status"] == "PASS"
        and row["evidence_pack_gate_status"] == "PASS"
        and row["ci_environment_status"] == "PASS"
        and row["ci_environment_type"] == "ci_environment_manifest"
        and row["nested_fixture_status"] == "PASS"
        and row["multi_schema_status"] == "PASS"
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())