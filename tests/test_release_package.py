import tarfile
import zipfile
from pathlib import Path

from scripts.assert_release_package import inspect_dist_dir, inspect_package


def test_manifest_includes_security_and_hygiene_docs():
    root = Path(__file__).resolve().parents[1]
    manifest = (root / "MANIFEST.in").read_text(encoding="utf-8")

    assert "include SECURITY.md" in manifest
    assert "recursive-include docs *.md" in manifest
    assert "prune mbs_product_readiness_audit" in manifest
    assert "include tests/test_release_hygiene.py" in manifest
    assert "include tests/test_leonardo_hpc_crosscheck.py" in manifest
    assert "include tests/test_leonardo_shell_wrappers.py" in manifest
    assert "include tests/test_enterprise_external_evidence.py" in manifest


def test_release_package_inspector_accepts_clean_sdist_and_wheel(tmp_path):
    sdist = tmp_path / "mbs-0.1.1.tar.gz"
    wheel = tmp_path / "mbs-0.1.1-py3-none-any.whl"

    with tarfile.open(sdist, "w:gz") as archive:
        for name in [
            "mbs-0.1.1/LICENSE",
            "mbs-0.1.1/README.md",
            "mbs-0.1.1/SECURITY.md",
            "mbs-0.1.1/MANIFEST.in",
            "mbs-0.1.1/pyproject.toml",
            "mbs-0.1.1/PKG-INFO",
            "mbs-0.1.1/docs/mbs_compliance_security_boundary.md",
            "mbs-0.1.1/docs/mbs_agent_tool_contract_v1.md",
            "mbs-0.1.1/docs/mbs_enterprise_blocker_disposition.md",
            "mbs-0.1.1/docs/mbs_enterprise_compatibility_matrix.md",
            "mbs-0.1.1/docs/mbs_release_readiness_checklist.md",
            "mbs-0.1.1/docs/mbs_security_privacy_release_hygiene.md",
            "mbs-0.1.1/docs/mbs_cli_command_matrix_20260517.md",
            "mbs-0.1.1/docs/mbs_enterprise_external_evidence_requests.md",
            "mbs-0.1.1/mbs/__init__.py",
            "mbs-0.1.1/mbs/cli.py",
            "mbs-0.1.1/scripts/classify_release_artifacts.py",
            "mbs-0.1.1/scripts/assert_fresh_install.py",
            "mbs-0.1.1/scripts/assert_release_package.py",
            "mbs-0.1.1/scripts/run_adversarial_hard_schema_pack.py",
            "mbs-0.1.1/scripts/run_multi_schema_fixture_bundle.py",
            "mbs-0.1.1/scripts/run_nested_provider_evidence.py",
            "mbs-0.1.1/scripts/assert_remote_ci_matrix_evidence.py",
            "mbs-0.1.1/scripts/assert_legacy_remote_ci_evidence.py",
            "mbs-0.1.1/scripts/run_serious_workflow_provider_evidence.py",
            "mbs-0.1.1/scripts/write_ci_environment.py",
            "mbs-0.1.1/tests/test_adversarial_hard_schema_pack.py",
            "mbs-0.1.1/tests/test_artifact_classification.py",
            "mbs-0.1.1/tests/test_cli_command_matrix_docs.py",
            "mbs-0.1.1/tests/test_ci_release_workflow.py",
            "mbs-0.1.1/tests/test_fresh_install.py",
            "mbs-0.1.1/tests/test_enterprise_external_evidence.py",
            "mbs-0.1.1/tests/test_leonardo_hpc_crosscheck.py",
            "mbs-0.1.1/tests/test_leonardo_shell_wrappers.py",
            "mbs-0.1.1/tests/test_multi_schema_fixture_bundle.py",
            "mbs-0.1.1/tests/test_nested_provider_evidence.py",
            "mbs-0.1.1/tests/test_release_hygiene.py",
            "mbs-0.1.1/tests/test_release_package.py",
            "mbs-0.1.1/benchmarks/results/sample_benchmark.json",
            "mbs-0.1.1/benchmarks/results/sample_benchmark.md",
        ]:
            path = tmp_path / name.replace("/", "__")
            path.write_text("ok", encoding="utf-8")
            archive.add(path, arcname=name)

    with zipfile.ZipFile(wheel, "w") as archive:
        for name in [
            "mbs/__init__.py",
            "mbs/cli.py",
            "mbs/agent_tools.py",
            "mbs_compiler.py",
            "mbs-0.1.1.dist-info/METADATA",
            "mbs-0.1.1.dist-info/entry_points.txt",
        ]:
            archive.writestr(name, "ok")

    assert inspect_package(sdist)["status"] == "PASS"
    assert inspect_package(wheel)["status"] == "PASS"
    assert inspect_dist_dir(tmp_path)["status"] == "PASS"


def test_release_package_inspector_rejects_forbidden_local_artifacts(tmp_path):
    sdist = tmp_path / "mbs-0.1.1.tar.gz"

    with tarfile.open(sdist, "w:gz") as archive:
        for name in [
            "mbs-0.1.1/LICENSE",
            "mbs-0.1.1/README.md",
            "mbs-0.1.1/SECURITY.md",
            "mbs-0.1.1/MANIFEST.in",
            "mbs-0.1.1/pyproject.toml",
            "mbs-0.1.1/PKG-INFO",
            "mbs-0.1.1/docs/mbs_security_privacy_release_hygiene.md",
            "mbs-0.1.1/mbs/__init__.py",
            "mbs-0.1.1/mbs/cli.py",
            "mbs-0.1.1/tests/test_release_hygiene.py",
            "mbs-0.1.1/.audit_venv/pyvenv.cfg",
        ]:
            path = tmp_path / name.replace("/", "__")
            path.write_text("ok", encoding="utf-8")
            archive.add(path, arcname=name)

    result = inspect_package(sdist)

    assert result["status"] == "FAIL"
    assert any(".audit_venv" in path for path in result["forbidden_packaged_paths"])