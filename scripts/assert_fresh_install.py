"""Prove a built MBS wheel can be installed and used from a clean environment.

This is intentionally a black-box install smoke test: it creates a temporary
virtual environment, installs the built wheel from dist/, and runs import + CLI
commands without relying on the source checkout being importable.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _console_script(venv_dir: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / f"{name}.exe"
    return venv_dir / "bin" / name


def _latest_wheel(dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("mbs-*.whl"), key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    if not wheels:
        raise FileNotFoundError(f"No MBS wheel found in {dist_dir}")
    return wheels[0]


def assert_fresh_install(dist_dir: Path, repo_root: Path, keep_venv: bool = False) -> dict[str, Any]:
    wheel = _latest_wheel(dist_dir)
    temp_root = Path(tempfile.mkdtemp(prefix="mbs_fresh_install_"))
    venv_dir = temp_root / "venv"
    proof_dir = temp_root / "proof"
    proof_dir.mkdir(parents=True, exist_ok=True)

    commands: list[dict[str, Any]] = []
    status = "PASS"
    failure_reason: str | None = None

    try:
        commands.append(_run([sys.executable, "-m", "venv", str(venv_dir)]))
        python = _venv_python(venv_dir)
        if commands[-1]["returncode"] != 0:
            raise RuntimeError("venv creation failed")

        env = os.environ.copy()
        # Prevent the source checkout from masking missing wheel package files.
        env.pop("PYTHONPATH", None)

        commands.append(_run([str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)], env=env))
        if commands[-1]["returncode"] != 0:
            raise RuntimeError("wheel install failed")

        import_check = (
            "import json, mbs, mbs.cli; "
            "print(json.dumps({'version': getattr(mbs, '__version__', None), 'cli': mbs.cli.__name__}))"
        )
        commands.append(_run([str(python), "-c", import_check], cwd=proof_dir, env=env))
        if commands[-1]["returncode"] != 0:
            raise RuntimeError("installed import check failed")

        mbs_exe = _console_script(venv_dir, "mbs")
        commands.append(_run([str(mbs_exe), "--help"], cwd=proof_dir, env=env))
        if commands[-1]["returncode"] != 0:
            raise RuntimeError("installed mbs --help failed")

        schema = repo_root / "examples" / "fintech_transaction_risk" / "schema.json"
        output = repo_root / "examples" / "fintech_transaction_risk" / "output.json"
        commands.append(
            _run(
                [str(mbs_exe), "validate", "--schema", str(schema), "--output", str(output), "--json"],
                cwd=proof_dir,
                env=env,
            )
        )
        if commands[-1]["returncode"] != 0:
            raise RuntimeError("installed mbs validate failed")

        try:
            validation_payload = json.loads(commands[-1]["stdout"])
        except json.JSONDecodeError as exc:
            raise RuntimeError("installed mbs validate did not emit JSON") from exc
        if validation_payload.get("status") != "PASS":
            raise RuntimeError(f"installed mbs validate returned {validation_payload.get('status')!r}")

    except Exception as exc:  # pragma: no cover - surfaced through CLI exit status
        status = "FAIL"
        failure_reason = str(exc)
    finally:
        if not keep_venv:
            shutil.rmtree(temp_root, ignore_errors=True)

    return {
        "status": status,
        "failure_reason": failure_reason,
        "wheel": str(wheel),
        "commands": commands,
        "kept_venv": str(venv_dir) if keep_venv else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assert the built MBS wheel works from a fresh venv.")
    parser.add_argument("--dist-dir", default="dist", help="Directory containing built wheel artifacts.")
    parser.add_argument("--repo-root", default=".", help="Repository root containing example fixtures.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument("--keep-venv", action="store_true", help="Keep the temporary venv for debugging.")
    args = parser.parse_args(argv)

    result = assert_fresh_install(Path(args.dist_dir), Path(args.repo_root).resolve(), keep_venv=args.keep_venv)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"MBS fresh install check: {result['status']}")
        print(f"- wheel: {result['wheel']}")
        if result["failure_reason"]:
            print(f"- failure_reason: {result['failure_reason']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
