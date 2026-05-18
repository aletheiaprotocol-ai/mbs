from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "mbs-ci.yml"


def test_ci_workflow_runs_release_gates_on_three_operating_systems():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "runs-on: ${{ matrix.os }}" in workflow
    assert "fail-fast: false" in workflow
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "macos-latest" in workflow
    assert "python-version: ['3.11']" in workflow


def test_ci_workflow_builds_installs_and_classifies_release_artifacts():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    required_steps = [
        "python -m pytest -q",
        "python scripts/write_ci_environment.py --out benchmarks/results/ci_environment.json",
        "python -m build",
        "python scripts/assert_release_package.py --dist-dir dist",
        "python scripts/assert_fresh_install.py --dist-dir dist",
        "python scripts/classify_release_artifacts.py",
        "--fail-on-review",
        "python scripts/run_multi_schema_fixture_bundle.py --out-dir benchmarks/results/multi_schema_fixture_bundle",
        "python scripts/assert_ci_artifacts.py --results-dir benchmarks/results",
    ]
    for step in required_steps:
        assert step in workflow


def test_ci_artifact_uploads_are_matrix_scoped():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "mbs-ci-artifacts-${{ matrix.os }}-py${{ matrix.python-version }}" in workflow
    assert "benchmarks/results/ci_environment.json" in workflow
    assert "benchmarks/results/multi_schema_fixture_bundle/**" in workflow
