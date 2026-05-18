"""Assert that MBS release package artifacts have expected hygiene boundaries.

This script checks built source distributions and wheels for required metadata,
required release docs, and accidentally packaged local artifacts. It is designed
to run after a release build, for example against files in ``dist/``.
"""

from __future__ import annotations

import argparse
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Any


FORBIDDEN_PATH_PARTS = {
    ".audit_venv",
    ".clean_install_venv",
    ".git",
    ".mbs_audit_venv",
    ".pytest_cache",
    ".venv",
    ".venv_smoke",
    "__pycache__",
    "build",
    "mbs_product_readiness_audit",
}

ALLOWED_BENCHMARK_RESULT_SUFFIXES = {
    "benchmarks/results/sample_benchmark.json",
    "benchmarks/results/sample_benchmark.md",
}

REQUIRED_SDIST_SUFFIXES = {
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "MANIFEST.in",
    "pyproject.toml",
    "docs/mbs_compliance_security_boundary.md",
    "docs/mbs_agent_tool_contract_v1.md",
    "docs/mbs_enterprise_blocker_disposition.md",
    "docs/mbs_enterprise_compatibility_matrix.md",
    "docs/mbs_release_readiness_checklist.md",
    "docs/mbs_security_privacy_release_hygiene.md",
    "docs/mbs_cli_command_matrix_20260517.md",
    "mbs/__init__.py",
    "mbs/cli.py",
    "scripts/classify_release_artifacts.py",
    "scripts/assert_fresh_install.py",
    "scripts/assert_release_package.py",
    "scripts/run_adversarial_hard_schema_pack.py",
    "scripts/run_multi_schema_fixture_bundle.py",
    "scripts/run_nested_provider_evidence.py",
    "scripts/assert_remote_ci_matrix_evidence.py",
    "scripts/assert_legacy_remote_ci_evidence.py",
    "scripts/run_serious_workflow_provider_evidence.py",
    "scripts/write_ci_environment.py",
    "docs/mbs_enterprise_external_evidence_requests.md",
    "tests/test_adversarial_hard_schema_pack.py",
    "tests/test_artifact_classification.py",
    "tests/test_cli_command_matrix_docs.py",
    "tests/test_ci_release_workflow.py",
    "tests/test_fresh_install.py",
    "tests/test_multi_schema_fixture_bundle.py",
    "tests/test_nested_provider_evidence.py",
    "tests/test_enterprise_external_evidence.py",
    "tests/test_release_hygiene.py",
    "tests/test_release_package.py",
}

REQUIRED_WHEEL_SUFFIXES = {
    "mbs/__init__.py",
    "mbs/cli.py",
    "mbs/agent_tools.py",
    "mbs_compiler.py",
}


def inspect_package(path: Path) -> dict[str, Any]:
    names = _archive_names(path)
    normalized = [_normalize_name(name) for name in names]
    forbidden = sorted(name for name in normalized if _is_forbidden_packaged_path(name))

    if path.name.endswith(".tar.gz"):
        required = REQUIRED_SDIST_SUFFIXES
        package_type = "sdist"
    elif path.suffix == ".whl":
        required = REQUIRED_WHEEL_SUFFIXES
        package_type = "wheel"
    else:
        return {"path": str(path), "status": "FAIL", "error": "unsupported package type"}

    missing = sorted(item for item in required if not _has_suffix(normalized, item))
    metadata_ok = _metadata_present(normalized, package_type)
    status = "PASS" if not missing and not forbidden and metadata_ok else "FAIL"
    return {
        "path": str(path),
        "package_type": package_type,
        "status": status,
        "file_count": len(normalized),
        "missing_required": missing,
        "forbidden_packaged_paths": forbidden,
        "metadata_present": metadata_ok,
    }


def inspect_dist_dir(dist_dir: Path) -> dict[str, Any]:
    packages = sorted([*dist_dir.glob("*.tar.gz"), *dist_dir.glob("*.whl")])
    inspections = [inspect_package(path) for path in packages]
    status = "PASS" if packages and all(item["status"] == "PASS" for item in inspections) else "FAIL"
    return {"status": status, "package_count": len(packages), "packages": inspections}


def _archive_names(path: Path) -> list[str]:
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            return archive.getnames()
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    return []


def _normalize_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def _has_suffix(names: list[str], suffix: str) -> bool:
    suffix = suffix.replace("\\", "/")
    return any(name == suffix or name.endswith("/" + suffix) for name in names)


def _metadata_present(names: list[str], package_type: str) -> bool:
    if package_type == "sdist":
        return _has_suffix(names, "PKG-INFO")
    return any(name.endswith(".dist-info/METADATA") for name in names) and any(
        name.endswith(".dist-info/entry_points.txt") for name in names
    )


def _is_forbidden_packaged_path(name: str) -> bool:
    parts = Path(name).parts
    if set(parts) & FORBIDDEN_PATH_PARTS:
        return True
    if "results" not in parts:
        return False
    if any(name.endswith("/" + allowed) or name == allowed for allowed in ALLOWED_BENCHMARK_RESULT_SUFFIXES):
        return False
    if name.endswith("/benchmarks/results") or name == "benchmarks/results":
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assert MBS release package hygiene")
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = inspect_dist_dir(Path(args.dist_dir))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"MBS release package check: {result['status']}")
        for package in result["packages"]:
            print(f"- {package['package_type']} {package['path']}: {package['status']}")
            for missing in package.get("missing_required", []):
                print(f"  missing: {missing}")
            for forbidden in package.get("forbidden_packaged_paths", []):
                print(f"  forbidden: {forbidden}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())