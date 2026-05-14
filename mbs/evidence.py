"""Evidence artifact packs for MBS benchmark results."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .gate import evaluate_gate, format_gate, load_gate_config, write_gate_json
from .report import aggregate_results, expand_paths, markdown_report, trace_errors
from .triage import format_triage, triage_results, write_triage_json


CLASSIFICATIONS = {
    "demo": "demo_or_software_check_not_model_benchmark",
    "ci": "ci_regression_check_not_broad_model_benchmark",
    "fixture": "fixture_smoke_not_provider_benchmark",
    "provider": "real_provider_behavior_evidence",
    "oss": "open_source_model_behavior_evidence",
    "hpc": "hpc_model_behavior_evidence",
}


def build_evidence_pack(
    results: list[str | Path],
    out_dir: str | Path,
    *,
    classification: str = "ci",
    gate_config: str | Path | None = None,
    exclude_infra: bool = False,
    require_traces: bool = True,
    copy_results: bool = False,
    title: str = "MBS Evidence Pack",
) -> dict[str, Any]:
    """Build a reviewable evidence directory from MBS result files."""
    result_files = expand_paths(results)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    report = aggregate_results([str(path) for path in result_files], exclude_infra=exclude_infra)
    report_errors = trace_errors(report) if require_traces else []
    report_md = markdown_report(report, summary_only=True)
    (out / "report.md").write_text(report_md, encoding="utf-8")
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    gate_result: dict[str, Any] | None = None
    if gate_config:
        gate_result = evaluate_gate([str(path) for path in result_files], config=load_gate_config(gate_config), exclude_infra=exclude_infra)
        write_gate_json(out / "gate.json", gate_result)
        (out / "gate.md").write_text(format_gate(gate_result), encoding="utf-8")

    triage = triage_results(
        [str(path) for path in result_files],
        min_schema_valid_rate=0.0,
        min_valid_json_rate=0.0,
        require_traces=require_traces,
    )
    write_triage_json(out / "triage.json", triage)
    (out / "triage.md").write_text(format_triage(triage), encoding="utf-8")

    copied_results: list[str] = []
    if copy_results:
        raw_dir = out / "raw_results"
        raw_dir.mkdir(exist_ok=True)
        for file_path in result_files:
            target = _unique_target(raw_dir, file_path.name)
            shutil.copy2(file_path, target)
            copied_results.append(str(target.relative_to(out)))

    classification_label = CLASSIFICATIONS.get(classification, classification)
    manifest = {
        "title": title,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "classification": classification_label,
        "classification_key": classification,
        "evidence_boundary": _evidence_boundary(classification_label),
        "result_files": [str(path) for path in result_files],
        "copied_results": copied_results,
        "artifacts": {
            "report_markdown": "report.md",
            "report_json": "report.json",
            "triage_markdown": "triage.md",
            "triage_json": "triage.json",
            "gate_markdown": "gate.md" if gate_result is not None else None,
            "gate_json": "gate.json" if gate_result is not None else None,
        },
        "checks": {
            "result_files": len(result_files),
            "report_rows": report.get("summary", {}).get("rows", 0),
            "trace_errors": report_errors,
            "gate_status": gate_result.get("status") if gate_result else None,
            "triage_status": triage.get("status"),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (out / "README.md").write_text(_readme(manifest, report, gate_result, triage), encoding="utf-8")
    return manifest


def _evidence_boundary(classification: str) -> str:
    if "not" in classification:
        return "This pack is useful for software/regression review, but it is not broad model benchmark evidence."
    return "This pack may be used as model-behavior evidence only for the listed schemas, cases, models, modes, and run settings."


def _readme(manifest: dict[str, Any], report: dict[str, Any], gate: dict[str, Any] | None, triage: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        f"# {manifest['title']}",
        "",
        f"Classification: `{manifest['classification']}`",
        "",
        manifest["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Result files: {manifest['checks']['result_files']}",
        f"- Report rows: {summary.get('rows', 0)}",
        f"- Total runs: {summary.get('total_runs', 0)}",
        f"- Infra-failed rows: {summary.get('infra_failed_rows', 0)}",
        f"- Traceable case rows: {summary.get('traceable_case_rows', 0)}",
        f"- Missing trace rows: {summary.get('missing_trace_rows', 0)}",
        f"- Mean schema-valid rate: {_fmt(summary.get('mean_schema_valid_rate'))}",
        f"- Mean semantic-correct rate: {_fmt(summary.get('mean_semantic_correct_rate'))}",
        f"- Mean clean-JSON rate: {_fmt(summary.get('mean_clean_json_rate'))}",
        f"- Gate status: {gate.get('status') if gate else 'not run'}",
        f"- Triage status: {triage.get('status')}",
        "",
        "## Artifacts",
        "",
        "- `manifest.json` — machine-readable pack manifest and evidence boundary",
        "- `report.md` / `report.json` — scorecards and aggregate metrics",
        "- `triage.md` / `triage.json` — failure and trace review",
    ]
    if gate:
        lines.append("- `gate.md` / `gate.json` — threshold pass/fail evidence")
    if manifest.get("copied_results"):
        lines.append("- `raw_results/` — copied result JSON files")
    return "\n".join(lines) + "\n"


def _unique_target(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        alt = directory / f"{stem}_{index}{suffix}"
        if not alt.exists():
            return alt
        index += 1


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)
