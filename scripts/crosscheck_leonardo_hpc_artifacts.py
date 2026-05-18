"""Cross-check mirrored Leonardo HF-local artifacts with standard MBS tooling.

The Leonardo runner is intentionally self-contained for cluster portability. This
script replays its mirrored `responses.jsonl` files through the package APIs used
by the normal CLI/report/gate path, so HPC evidence has a second local MBS check.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from mbs.adapter import adapt_response_jsonl
from mbs.gate import evaluate_gate, write_gate_json
from mbs.report import aggregate_results


DEFAULT_ROOT = Path("benchmarks/results/leonardo_mbs_hpc_20260517")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="summary JSON path; defaults to <root>/standard_mbs_crosscheck_summary.json",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing standard MBS cross-check files")
    args = parser.parse_args(argv)

    root = args.root
    if not root.exists():
        raise SystemExit(f"root does not exist: {root}")

    schema, cases = _load_runner_contract()
    processed: list[dict[str, Any]] = []
    result_paths: list[Path] = []
    for responses_path in sorted(root.rglob("responses.jsonl")):
        model_dir = responses_path.parent
        cross_dir = model_dir / "standard_mbs"
        result_path = cross_dir / "result.json"
        if result_path.exists() and not args.force:
            result_paths.append(result_path)
            processed.append(_record(model_dir, result_path, skipped=True))
            continue

        cross_dir.mkdir(parents=True, exist_ok=True)
        schema_path = cross_dir / "schema.json"
        cases_path = cross_dir / "cases.jsonl"
        schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
        cases_path.write_text(
            "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
            encoding="utf-8",
        )

        manifest = _read_json(model_dir / "manifest.json")
        payload = adapt_response_jsonl(
            schema_path,
            responses_path,
            cases_path=cases_path,
            model=str(manifest.get("model") or model_dir.name),
            prompt_style="full",
            decoding_mode="hf_local_replay",
        )
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        report = aggregate_results([result_path], exclude_infra=False)
        (cross_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        gate = evaluate_gate([result_path], exclude_infra=False)
        write_gate_json(cross_dir / "gate.json", gate)
        result_paths.append(result_path)
        processed.append(_record(model_dir, result_path, skipped=False))

    aggregate = aggregate_results(result_paths, exclude_infra=False) if result_paths else {}
    aggregate_gate = evaluate_gate(result_paths, exclude_infra=False) if result_paths else {"status": "FAIL", "reason": "no rows"}
    summary = {
        "root": str(root),
        "processed_count": len(processed),
        "result_files": [str(path) for path in result_paths],
        "aggregate_summary": aggregate.get("summary", {}),
        "aggregate_gate": aggregate_gate,
        "processed": processed,
    }
    out_path = args.out or (root / "standard_mbs_crosscheck_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary["aggregate_summary"], indent=2, sort_keys=True))
    print(f"wrote {out_path}")
    return 0


def _load_runner_contract() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    runner_path = Path(__file__).with_name("leonardo_mbs_hf_matrix.py")
    spec = importlib.util.spec_from_file_location("leonardo_mbs_hf_matrix", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runner module: {runner_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    schema = getattr(module, "NESTED_SCHEMA")
    cases_jsonl = getattr(module, "CASES_JSONL")
    cases = [json.loads(line) for line in cases_jsonl.splitlines() if line.strip()]
    return schema, cases


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _record(model_dir: Path, result_path: Path, *, skipped: bool) -> dict[str, Any]:
    manifest = _read_json(model_dir / "manifest.json")
    gate = _read_json(result_path.parent / "gate.json") if result_path.exists() else {}
    summary = _read_json(result_path).get("summary", {}) if result_path.exists() else {}
    return {
        "model": manifest.get("model") or model_dir.name,
        "suite": model_dir.parent.name,
        "result": str(result_path),
        "skipped": skipped,
        "gate_status": gate.get("status"),
        "runs": summary.get("runs"),
        "schema_valid_rate": summary.get("schema_valid_rate"),
        "semantic_correct_rate": summary.get("semantic_correct_rate"),
        "clean_json_rate": summary.get("clean_json_rate"),
    }


if __name__ == "__main__":
    raise SystemExit(main())