import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_nested_provider_evidence_dry_run_writes_no_evidence_plan(tmp_path):
    out_dir = tmp_path / "dry_run"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_nested_provider_evidence.py",
            "--model",
            "local-test-model",
            "--classification",
            "oss",
            "--mode",
            "tool_call",
            "--out-dir",
            str(out_dir),
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
    assert "No model evidence was collected" in manifest["evidence_boundary"]
    assert manifest["classification"] == "open_source_model_behavior_evidence"
    assert (out_dir / "response_template.jsonl").exists()
    assert "tool_call" in (out_dir / "response_template.jsonl").read_text(encoding="utf-8").splitlines()[0]


def test_nested_provider_evidence_dry_run_can_plan_ollama_collection(tmp_path):
    out_dir = tmp_path / "ollama_dry_run"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_nested_provider_evidence.py",
            "--model",
            "llama3.2:1b",
            "--classification",
            "oss",
            "--mode",
            "tool_call",
            "--runner",
            "ollama",
            "--out-dir",
            str(out_dir),
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
    run_plan = json.loads((out_dir / "run_plan.json").read_text(encoding="utf-8"))
    collect_command = run_plan["commands"][0]
    assert manifest["status"] == "NO_EVIDENCE_DRY_RUN"
    assert manifest["run_metadata"]["runner"] == "ollama"
    assert run_plan["runner"] == "ollama"
    assert "scripts/collect_ollama_responses.py" in collect_command
    assert "http://localhost:11434" in collect_command


def test_nested_provider_evidence_dry_run_can_plan_lm_studio_collection(tmp_path):
    out_dir = tmp_path / "lm_studio_dry_run"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_nested_provider_evidence.py",
            "--model",
            "local-model",
            "--classification",
            "oss",
            "--mode",
            "json_mode",
            "--runner",
            "lm-studio",
            "--out-dir",
            str(out_dir),
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
    run_plan = json.loads((out_dir / "run_plan.json").read_text(encoding="utf-8"))
    collect_command = run_plan["commands"][0]
    assert manifest["status"] == "NO_EVIDENCE_DRY_RUN"
    assert manifest["run_metadata"]["runner"] == "lm-studio"
    assert run_plan["runner"] == "lm-studio"
    assert "scripts/collect_azure_openai_responses.py" in collect_command
    assert "--provider" in collect_command
    assert "openai-compatible" in collect_command
    assert "http://localhost:1234" in collect_command
    assert "LM_STUDIO_API_KEY" in collect_command


def test_nested_provider_evidence_builds_classified_pack_from_response_jsonl(tmp_path):
    out_dir = tmp_path / "provider_pack"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_nested_provider_evidence.py",
            "--responses",
            "examples/nested_tool_arguments/provider_tool_call_good.jsonl",
            "--model",
            "fixture-provider-model",
            "--classification",
            "provider",
            "--mode",
            "tool_call",
            "--out-dir",
            str(out_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["classification"] == "real_provider_behavior_evidence"
    assert "Not a broad provider/model claim" in manifest["evidence_boundary"]
    assert manifest["checks"]["runs"] == 25
    assert manifest["checks"]["traceable_case_rows"] == 25
    assert manifest["checks"]["missing_trace_rows"] == 0
    assert manifest["checks"]["schema_valid_rate"] == 1.0
    assert manifest["checks"]["semantic_correct_rate"] == 1.0
    assert manifest["checks"]["gate_status"] == "PASS"
    assert manifest["checks"]["artifact_classification_status"] in {"PASS", "REVIEW"}
    assert (out_dir / "evidence_pack" / "manifest.json").exists()
    assert (out_dir / "evidence_pack" / "raw_results").exists()


def test_nested_provider_evidence_blocks_secret_bearing_response_file(tmp_path):
    responses = tmp_path / "provider_secret.responses.jsonl"
    fake_secret = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    responses.write_text(
        json.dumps({"case_id": "nested_001", "output": {"leak": fake_secret}}) + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "blocked"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_nested_provider_evidence.py",
            "--responses",
            str(responses),
            "--model",
            "provider-model",
            "--classification",
            "provider",
            "--out-dir",
            str(out_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "FAIL"
    assert manifest["failure_reason"] == "blocking_secret_or_artifact_classification_failure"
    assert manifest["artifact_classification"]["blocking_findings_count"] == 1