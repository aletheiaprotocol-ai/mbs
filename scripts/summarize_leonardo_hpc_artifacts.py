"""Summarize mirrored Leonardo HF-local MBS artifacts.

This intentionally reads only the portable `manifest.json` files produced by the
Leonardo runner and skips derived `standard_mbs` cross-check directories.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("benchmarks/results/leonardo_mbs_hpc_20260517")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = summarize(args.root)
    out_path = args.out or args.root / "summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"rows {summary['count']}")
    for row in summary["rows"]:
        if row.get("run", "").startswith("compact_"):
            print(json.dumps(row, sort_keys=True))
    return 0


def summarize(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("manifest.json")):
        if "standard_mbs" in path.parts:
            continue
        manifest = _read_json(path)
        checks = manifest.get("checks", {}) if isinstance(manifest.get("checks"), dict) else {}
        rows.append(
            {
                "run": path.parent.parent.name,
                "model_dir": path.parent.name,
                "model": manifest.get("model"),
                "suite": manifest.get("suite"),
                "prompt_style": manifest.get("prompt_style"),
                "status": manifest.get("status"),
                "classification": manifest.get("classification"),
                "runs": checks.get("runs"),
                "behavior_runs": checks.get("behavior_runs"),
                "infra_failed_rows": checks.get("infra_failed_rows"),
                "schema_valid_rate": checks.get("schema_valid_rate"),
                "semantic_correct_rate": checks.get("semantic_correct_rate"),
                "clean_json_rate": checks.get("clean_json_rate"),
                "gate_status": checks.get("gate_status"),
                "load_error": manifest.get("load_error"),
                "manifest": str(path),
            }
        )
    return {"root": str(root), "count": len(rows), "rows": rows}


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())