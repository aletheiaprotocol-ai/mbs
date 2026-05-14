import importlib.util
import json
from pathlib import Path


REQUIRED_LANGUAGES = {"ar", "de", "en", "es", "fr", "hu", "tr"}
REQUIRED_DOMAINS = {"fintech", "procurement", "qme_source_review", "support", "tool_call_safety"}


def test_mbs_lang_fixture_cases_cover_sprint5_languages_and_domains():
    root = Path(__file__).resolve().parents[1]
    case_dir = root / "examples" / "multilingual_risk_review"
    rows = []
    for path in sorted(case_dir.glob("cases_*.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    assert len(rows) == 15
    assert {row["input_language"] for row in rows} == REQUIRED_LANGUAGES
    assert {row["domain"] for row in rows} == REQUIRED_DOMAINS
    assert all(row["output_language"] == "en" for row in rows)
    assert all(row.get("fixture_output") for row in rows)


def test_mbs_lang_matrix_manifest_exposes_sprint5_metrics(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "run_mbs_lang_matrix.py"
    spec = importlib.util.spec_from_file_location("run_mbs_lang_matrix", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        "sys.argv",
        ["run_mbs_lang_matrix.py", "--root", str(root), "--out-dir", str(tmp_path), "--json"],
    )

    assert module.main() == 0
    manifest = json.loads(capsys.readouterr().out)
    matrix = json.loads((tmp_path / "mbs_lang_matrix.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "PASS"
    assert manifest["classification"] == "fixture_mbs_lang_matrix_not_provider_benchmark"
    assert set(manifest["checks"]["domains"]) == REQUIRED_DOMAINS
    assert manifest["checks"]["schema_valid_rate"] == 1.0
    assert manifest["checks"]["semantic_correct_rate"] == 1.0
    assert manifest["checks"]["language_mismatch_rate"] == 0.0
    assert manifest["checks"]["cost_per_valid_output_tokens"] > 0
    assert matrix["summary"]["rows"] == 15
    assert matrix["summary"]["valid_outputs"] == 15
    assert matrix["summary"]["failed_outputs"] == 0
    assert "not provider/model" in matrix["evidence_boundary"]
