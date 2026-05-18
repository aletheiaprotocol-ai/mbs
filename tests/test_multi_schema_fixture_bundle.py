import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_multi_schema_fixture_bundle_builds_traceable_costed_manifest(tmp_path):
    out_dir = tmp_path / "multi_schema_fixture_bundle"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_multi_schema_fixture_bundle.py",
            "--out-dir",
            str(out_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["classification"] == "fixture_smoke_not_provider_benchmark"
    assert manifest["evidence_boundary"]["not_provider_benchmark"] is True
    assert manifest["checks"]["result_files"] == 4
    assert manifest["checks"]["report_rows"] == 4
    assert len(manifest["checks"]["schemas"]) == 4
    assert len(manifest["checks"]["models"]) == 4
    assert manifest["checks"]["total_runs"] == 49
    assert manifest["checks"]["traceable_case_rows"] == 49
    assert manifest["checks"]["missing_trace_rows"] == 0
    assert manifest["checks"]["gate_status"] == "PASS"
    assert manifest["checks"]["cost_per_valid_output_present"] is True
    assert (out_dir / "evidence_pack" / "report.md").exists()
    assert (out_dir / "evidence_pack" / "gate.json").exists()
    assert (out_dir / "README.md").exists()
