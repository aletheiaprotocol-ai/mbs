"""Write a non-secret CI environment manifest for evidence artifacts."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_manifest() -> dict[str, object]:
    return {
        "status": "PASS",
        "evidence_type": "ci_environment_manifest",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner_os": os.getenv("RUNNER_OS") or platform.system(),
        "github_workflow": os.getenv("GITHUB_WORKFLOW"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "python_version": platform.python_version(),
        "python_executable_name": Path(sys.executable).name,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "secret_boundary": "No environment variables or credentials are serialized.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write MBS CI environment manifest")
    parser.add_argument("--out", type=Path, default=Path("benchmarks/results/ci_environment.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    manifest = build_manifest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())