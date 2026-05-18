"""Build or plan provider evidence for the three serious workflow packs.

The script is intentionally credential-free. In dry-run mode it writes exact
collection/build commands for each serious workflow. In evidence mode it consumes
reviewed response JSONL files already collected by a secret-aware process and
builds provider-classified MBS evidence packs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = {
    "incident_response_runbook": {
        "schema": "examples/incident_response_runbook/schema.json",
        "cases": "examples/incident_response_runbook/cases.jsonl",
        "policy": "examples/incident_response_runbook/policy.md",
        "gate": "benchmarks/incident_response_gate.yaml",
    },
    "fintech_transaction_risk": {
        "schema": "examples/fintech_transaction_risk/schema.json",
        "cases": "examples/fintech_transaction_risk/cases.jsonl",
        "policy": "examples/fintech_transaction_risk/policy.md",
        "gate": "benchmarks/fintech_transaction_risk_gate.yaml",
    },
    "support_ticket_triage": {
        "schema": "examples/support_ticket_triage/schema.json",
        "cases": "examples/support_ticket_triage/cases.jsonl",
        "policy": "examples/support_ticket_triage/policy.md",
        "gate": "benchmarks/support_ticket_triage_gate.yaml",
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan or build serious-workflow provider evidence")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--out-dir", type=Path, default=Path("benchmarks/results/serious_workflow_provider_evidence"))
    parser.add_argument("--responses-dir", type=Path, help="Directory containing <workflow>.jsonl response files")
    parser.add_argument("--model", required=True)
    parser.add_argument("--classification", choices=["provider", "oss", "hpc"], default="provider")
    parser.add_argument("--mode", choices=["text", "json_mode", "tool_call"], default="tool_call")
    parser.add_argument("--runner", choices=["openai-compatible", "ollama", "lm-studio"], default="openai-compatible")
    parser.add_argument("--endpoint", help="Optional non-secret endpoint recorded in dry-run plans")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    out_dir = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        manifest = _dry_run_manifest(args, root, out_dir)
        _write_json(out_dir / "manifest.json", manifest)
        _write_json(out_dir / "run_plan.json", {"workflows": manifest["workflows"]})
        _emit(manifest, args.json)
        return 0

    if not args.responses_dir:
        raise SystemExit("--responses-dir is required unless --dry-run is set")
    responses_dir = args.responses_dir if args.responses_dir.is_absolute() else root / args.responses_dir
    workflow_rows = []
    for workflow, config in WORKFLOWS.items():
        responses = responses_dir / f"{workflow}.jsonl"
        workflow_out = out_dir / workflow
        command = _build_command(args, root, workflow_out, config, responses)
        if not responses.exists():
            workflow_rows.append({"workflow": workflow, "status": "MISSING_RESPONSES", "responses": str(responses)})
            continue
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        manifest_path = workflow_out / "manifest.json"
        manifest = _read_json(manifest_path)
        workflow_rows.append(
            {
                "workflow": workflow,
                "status": manifest.get("status", "FAIL" if result.returncode else "UNKNOWN"),
                "returncode": result.returncode,
                "responses": str(responses),
                "manifest": str(manifest_path),
                "gate_status": manifest.get("checks", {}).get("gate_status"),
                "runs": manifest.get("checks", {}).get("runs"),
            }
        )

    status = "PASS" if workflow_rows and all(row["status"] == "PASS" for row in workflow_rows) else "FAIL"
    manifest = {
        "status": status,
        "purpose": "provider-classified serious workflow evidence bundle",
        "classification": args.classification,
        "model": args.model,
        "mode": args.mode,
        "workflows": workflow_rows,
        "remaining_boundary": "All three serious workflows must PASS with reviewed non-secret response JSONL before closing the provider-classified workflow blocker.",
    }
    _write_json(out_dir / "manifest.json", manifest)
    _emit(manifest, args.json)
    return 0 if status == "PASS" else 2


def _dry_run_manifest(args: argparse.Namespace, root: Path, out_dir: Path) -> dict[str, Any]:
    rows = []
    for workflow, config in WORKFLOWS.items():
        workflow_out = out_dir / workflow
        responses = out_dir / "responses" / f"{workflow}.jsonl"
        command = _build_command(args, root, workflow_out, config, responses, dry_run=True)
        rows.append(
            {
                "workflow": workflow,
                "status": "NO_EVIDENCE_DRY_RUN",
                "schema": config["schema"],
                "cases": config["cases"],
                "policy": config["policy"],
                "gate": config["gate"],
                "expected_responses": str(responses),
                "command": command,
            }
        )
    return {
        "status": "NO_EVIDENCE_DRY_RUN",
        "purpose": "serious workflow provider evidence collection plan only",
        "model": args.model,
        "classification": args.classification,
        "mode": args.mode,
        "runner": args.runner,
        "workflows": rows,
        "next_step": "Collect reviewed non-secret response JSONL for each workflow, then rerun without --dry-run and with --responses-dir.",
    }


def _build_command(
    args: argparse.Namespace,
    root: Path,
    workflow_out: Path,
    config: dict[str, str],
    responses: Path,
    *,
    dry_run: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        "scripts/run_nested_provider_evidence.py",
        "--root",
        str(root),
        "--model",
        args.model,
        "--classification",
        args.classification,
        "--mode",
        args.mode,
        "--runner",
        args.runner,
        "--schema",
        config["schema"],
        "--cases",
        config["cases"],
        "--gate-config",
        config["gate"],
        "--out-dir",
        str(workflow_out),
    ]
    if args.endpoint:
        command.extend(["--endpoint", args.endpoint])
    if dry_run:
        command.append("--dry-run")
    else:
        command.extend(["--responses", str(responses)])
    return command


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Serious workflow provider evidence: {payload['status']}")


if __name__ == "__main__":
    raise SystemExit(main())