import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_PARTS = {
    ".git",
    ".audit_venv",
    ".clean_install_venv",
    ".mbs_audit_venv",
    ".pytest_cache",
    ".venv",
    ".venv_smoke",
    "__pycache__",
    "build",
    "dist",
    "mbs.egg-info",
    "results",
}

HIGH_CONFIDENCE_SECRET_PATTERNS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "huggingface_token": re.compile(r"hf_[A-Za-z0-9]{20,}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
}


def _release_relevant_text_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel_parts = set(path.relative_to(REPO_ROOT).parts)
        if rel_parts & SKIP_PARTS:
            continue
        yield path


def test_release_hygiene_docs_exist_and_define_boundaries():
    security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    hygiene = (REPO_ROOT / "docs" / "mbs_security_privacy_release_hygiene.md").read_text(encoding="utf-8")

    assert "Do not commit" in security
    assert "environment variables" in security
    assert "not a formal third-party security audit" in hygiene
    assert "Enterprise Pilot blocker" in hygiene


def test_release_blockers_define_required_disposition_fields():
    blockers = (REPO_ROOT / "mbs_enterprise_readiness" / "RELEASE_BLOCKERS.md").read_text(encoding="utf-8")

    assert "Every blocker must have:" in blockers
    for field in ["owner", "severity", "target readiness label", "planned fix", "verification command", "status", "date closed"]:
        assert field in blockers

    required_sections = [
        "## Blocks ENTERPRISE PILOT READY",
        "## Blocks ENTERPRISE PRODUCTION READY",
        "## Required blocker disposition",
    ]
    for section in required_sections:
        assert section in blockers

    pilot_lines = [line for line in blockers.splitlines() if re.match(r"\d+\. Gate ", line)]
    assert len(pilot_lines) == 10
    assert [int(line.split(".", 1)[0]) for line in pilot_lines] == list(range(1, 11))
    assert all(
        "missing" in line.lower()
        or "incomplete" in line.lower()
        or "not yet" in line.lower()
        or "failed" in line.lower()
        or "partial only" in line.lower()
        for line in pilot_lines
    )


def test_gitignore_excludes_local_audit_and_smoke_virtualenvs():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".audit_venv/" in gitignore
    assert "external_user_smoke_test/.venv_smoke/" in gitignore
    assert "results/" in gitignore


def test_release_relevant_files_do_not_contain_high_confidence_tokens():
    findings = []
    for path in _release_relevant_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in HIGH_CONFIDENCE_SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append(f"{path.relative_to(REPO_ROOT)}:{label}:{match.group(0)[:8]}...")

    assert findings == []