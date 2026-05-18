import json
import subprocess
import sys
from pathlib import Path

from scripts.assert_remote_ci_matrix_evidence import inspect_remote_ci_artifacts
from scripts.assert_legacy_remote_ci_evidence import inspect_legacy_remote_ci_artifact


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_remote_ci_matrix_evidence_accepts_three_complete_os_artifacts(tmp_path):
    for os_name in ["ubuntu-latest", "windows-latest", "macos-latest"]:
        root = tmp_path / f"mbs-ci-artifacts-{os_name}-py3.11"
        (root / "ci_report.md").parent.mkdir(parents=True, exist_ok=True)
        (root / "ci_report.md").write_text("ok", encoding="utf-8")
        _write_json(root / "ci_bench.json", {"summary": {"runs": 1}})
        _write_json(root / "ci_gate.json", {"status": "PASS"})
        _write_json(root / "ci_environment.json", {"status": "PASS", "evidence_type": "ci_environment_manifest", "runner_os": os_name})
        _write_json(root / "evidence_pack_ci" / "manifest.json", {"checks": {"gate_status": "PASS"}})
        _write_json(root / "nested_tool_fixture_pack" / "manifest.json", {"status": "PASS"})
        _write_json(root / "multi_schema_fixture_bundle" / "manifest.json", {"status": "PASS"})

    result = inspect_remote_ci_artifacts(tmp_path)

    assert result["status"] == "PASS"
    assert [row["os"] for row in result["rows"]] == ["ubuntu-latest", "windows-latest", "macos-latest"]


def test_remote_ci_matrix_evidence_accepts_github_preserved_artifact_paths(tmp_path):
    for os_name in ["ubuntu-latest", "windows-latest", "macos-latest"]:
        root = tmp_path / f"mbs-ci-artifacts-{os_name}-py3.11" / "benchmarks" / "results"
        (root / "ci_report.md").parent.mkdir(parents=True, exist_ok=True)
        (root / "ci_report.md").write_text("ok", encoding="utf-8")
        _write_json(root / "ci_bench.json", {"summary": {"runs": 1}})
        _write_json(root / "ci_gate.json", {"status": "PASS"})
        _write_json(
            root / "ci_environment.json",
            {"status": "PASS", "evidence_type": "ci_environment_manifest", "runner_os": os_name},
        )
        _write_json(root / "evidence_pack_ci" / "manifest.json", {"checks": {"gate_status": "PASS"}})
        _write_json(root / "nested_tool_fixture_pack" / "manifest.json", {"status": "PASS"})
        _write_json(root / "multi_schema_fixture_bundle" / "manifest.json", {"status": "PASS"})

    result = inspect_remote_ci_artifacts(tmp_path)

    assert result["status"] == "PASS"
    assert all(Path(row["artifact_root"]).parts[-2:] == ("benchmarks", "results") for row in result["rows"])


def test_remote_ci_matrix_evidence_fails_when_os_artifact_missing(tmp_path):
    result = inspect_remote_ci_artifacts(tmp_path)

    assert result["status"] == "FAIL"
    assert len(result["rows"]) == 3
    assert all(row["missing_files"] for row in result["rows"])


def test_legacy_remote_ci_evidence_accepts_single_ubuntu_artifact(tmp_path):
    root = tmp_path / "mbs-ci-artifacts" / "benchmarks" / "results"
    root.mkdir(parents=True)
    (root / "ci_report.md").write_text("ok", encoding="utf-8")
    _write_json(root / "ci_bench.json", {"summary": {"runs": 1}})
    _write_json(root / "ci_gate.json", {"status": "PASS"})
    _write_json(root / "evidence_pack_ci" / "manifest.json", {"checks": {"gate_status": "PASS"}})
    _write_json(root / "nested_tool_fixture_pack" / "manifest.json", {"status": "PASS"})

    result = inspect_legacy_remote_ci_artifact(tmp_path)

    assert result["status"] == "PASS"
    assert result["evidence_type"] == "legacy_remote_ubuntu_ci_execution"
    assert "not remote Windows/macOS" in result["remaining_boundary"]


def test_serious_workflow_provider_evidence_dry_run_writes_three_workflow_plan(tmp_path):
    out_dir = tmp_path / "serious_plan"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_serious_workflow_provider_evidence.py",
            "--model",
            "provider-model",
            "--out-dir",
            str(out_dir),
            "--classification",
            "provider",
            "--mode",
            "tool_call",
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "NO_EVIDENCE_DRY_RUN"
    assert len(manifest["workflows"]) == 3
    assert {row["workflow"] for row in manifest["workflows"]} == {
        "incident_response_runbook",
        "fintech_transaction_risk",
        "support_ticket_triage",
    }
    assert all("scripts/run_nested_provider_evidence.py" in row["command"] for row in manifest["workflows"])


def test_external_evidence_request_doc_lists_unblock_commands():
    doc = (REPO_ROOT / "docs" / "mbs_enterprise_external_evidence_requests.md").read_text(encoding="utf-8")

    assert "assert_remote_ci_matrix_evidence.py" in doc
    assert "run_serious_workflow_provider_evidence.py" in doc
    assert "Formal compliance/security review" in doc
    assert "Do not claim Enterprise" in doc


def test_write_ci_environment_manifest_contains_no_secret_values(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/write_ci_environment.py", "--out", str(tmp_path / "ci_environment.json"), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    manifest = json.loads((tmp_path / "ci_environment.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["evidence_type"] == "ci_environment_manifest"
    assert "No environment variables or credentials" in manifest["secret_boundary"]
    assert "api_key" not in json.dumps(manifest).lower()