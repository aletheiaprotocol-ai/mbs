"""Validate downloaded legacy single-run GitHub CI evidence.

The current public main branch may still publish one Ubuntu artifact named
``mbs-ci-artifacts``. This script records that evidence honestly as legacy
Ubuntu CI proof; it does not claim three-OS matrix evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "benchmarks/results/ci_bench.json",
    "benchmarks/results/ci_report.md",
    "benchmarks/results/ci_gate.json",
    "benchmarks/results/evidence_pack_ci/manifest.json",
    "benchmarks/results/nested_tool_fixture_pack/manifest.json",
)


def inspect_legacy_remote_ci_artifact(root: Path) -> dict[str, Any]:
    artifact_root = root / "mbs-ci-artifacts" if (root / "mbs-ci-artifacts").exists() else root
    missing = [name for name in REQUIRED_FILES if not (artifact_root / name).exists()]
    gate = _read_json(artifact_root / "benchmarks/results/ci_gate.json")
    evidence_manifest = _read_json(artifact_root / "benchmarks/results/evidence_pack_ci/manifest.json")
    nested_manifest = _read_json(artifact_root / "benchmarks/results/nested_tool_fixture_pack/manifest.json")
    checks = {
        "ci_gate_status": gate.get("status"),
        "evidence_pack_gate_status": evidence_manifest.get("checks", {}).get("gate_status"),
        "nested_fixture_status": nested_manifest.get("status"),
    }
    status = "PASS" if not missing and all(value == "PASS" for value in checks.values()) else "FAIL"
    return {
        "status": status,
        "evidence_type": "legacy_remote_ubuntu_ci_execution",
        "artifact_root": str(artifact_root),
        "missing_files": missing,
        "checks": checks,
        "remaining_boundary": "This is successful remote Ubuntu CI evidence only. It is not remote Windows/macOS matrix evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assert legacy single-artifact remote CI evidence")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("benchmarks/results/remote_ci_artifacts"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = inspect_legacy_remote_ci_artifact(args.artifacts_dir)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Legacy remote CI evidence: {result['status']}")
    return 0 if result["status"] == "PASS" else 2


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())