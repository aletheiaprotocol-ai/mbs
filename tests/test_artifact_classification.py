from pathlib import Path

from scripts.classify_release_artifacts import classify_artifact, classify_paths


def test_fixture_artifact_is_public_software_evidence(tmp_path):
    artifact = tmp_path / "benchmarks" / "results" / "sample_benchmark.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"status":"PASS"}', encoding="utf-8")

    result = classify_artifact(artifact, repo_root=tmp_path)

    assert result.evidence_class == "sample"
    assert result.sensitivity == "public"
    assert result.review_required is False
    assert "software/demo evidence" in result.sharing_boundary


def test_provider_artifact_requires_review(tmp_path):
    artifact = tmp_path / "results" / "provider_nested_tool_call" / "run.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"model":"provider-model","output":"ok"}', encoding="utf-8")

    result = classify_artifact(artifact, repo_root=tmp_path)

    assert result.evidence_class == "provider"
    assert result.sensitivity == "restricted_benchmark"
    assert result.review_required is True
    assert "provider/model/run settings" in result.sharing_boundary


def test_secret_finding_blocks_external_sharing(tmp_path):
    artifact = tmp_path / "docs" / "leaked.md"
    artifact.parent.mkdir(parents=True)
    fake_secret = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    artifact.write_text(f"token {fake_secret}", encoding="utf-8")

    result = classify_paths([artifact], repo_root=tmp_path)

    assert result["status"] == "FAIL"
    assert result["blocking_findings_count"] == 1
    assert result["artifacts"][0]["sensitivity"] == "blocked_secret"


def test_public_release_docs_are_classified_without_manual_review(tmp_path):
    readme = tmp_path / "README.md"
    security = tmp_path / "SECURITY.md"
    readme.write_text("# MBS\n", encoding="utf-8")
    security.write_text("Report privately to maintainers@example.com", encoding="utf-8")

    result = classify_paths([readme, security], repo_root=tmp_path)

    assert result["status"] == "PASS"
    assert result["review_required_count"] == 0
    assert {artifact["evidence_class"] for artifact in result["artifacts"]} == {"docs"}
