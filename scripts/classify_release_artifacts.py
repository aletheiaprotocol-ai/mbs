"""Classify MBS evidence/release artifacts before external sharing.

The classifier is conservative: every artifact gets an evidence class, a
sensitivity level, and an allowed sharing boundary. It is not a DLP product, but
it provides a repeatable release-review manifest for CI/local evidence packs.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}
SECRET_PATTERNS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "huggingface_token": re.compile(r"hf_[A-Za-z0-9]{20,}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
}
SENSITIVE_TEXT_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone_like": re.compile(r"\b(?:\+?\d[\d .()-]{7,}\d)\b"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
}

PUBLIC_OK_CLASSES = {"demo", "ci", "fixture", "docs", "sample"}
RESTRICTED_CLASSES = {"provider", "oss", "hpc", "unknown"}
PUBLIC_RELEASE_DOCS = {"readme.md", "security.md", "license", "manifest.in", "pyproject.toml"}


@dataclass(frozen=True)
class ArtifactClassification:
    path: str
    evidence_class: str
    sensitivity: str
    sharing_boundary: str
    review_required: bool
    findings: list[str]


def iter_artifact_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file():
                files.append(child)
    return sorted(files)


def classify_artifact(path: Path, *, repo_root: Path | None = None) -> ArtifactClassification:
    rel = _relative(path, repo_root)
    normalized = rel.replace("\\", "/")
    evidence_class = _evidence_class(normalized)
    findings = _findings(path)
    sensitivity = _sensitivity(evidence_class, findings, normalized)
    review_required = sensitivity != "public" or evidence_class in RESTRICTED_CLASSES
    sharing_boundary = _sharing_boundary(evidence_class, sensitivity)
    return ArtifactClassification(
        path=rel,
        evidence_class=evidence_class,
        sensitivity=sensitivity,
        sharing_boundary=sharing_boundary,
        review_required=review_required,
        findings=findings,
    )


def classify_paths(paths: Iterable[Path], *, repo_root: Path | None = None) -> dict[str, Any]:
    artifacts = [classify_artifact(path, repo_root=repo_root) for path in iter_artifact_files(paths)]
    counts: dict[str, int] = {}
    for artifact in artifacts:
        counts[artifact.evidence_class] = counts.get(artifact.evidence_class, 0) + 1
    blocking = [artifact for artifact in artifacts if any(item.startswith("secret:") for item in artifact.findings)]
    review = [artifact for artifact in artifacts if artifact.review_required]
    status = "FAIL" if blocking else "REVIEW" if review else "PASS"
    return {
        "status": status,
        "artifact_count": len(artifacts),
        "class_counts": counts,
        "review_required_count": len(review),
        "blocking_findings_count": len(blocking),
        "artifacts": [asdict(artifact) for artifact in artifacts],
    }


def _relative(path: Path, repo_root: Path | None) -> str:
    if repo_root:
        try:
            return str(path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            pass
    return str(path)


def _evidence_class(path: str) -> str:
    lower = path.lower()
    if lower in PUBLIC_RELEASE_DOCS:
        return "docs"
    if lower.endswith("docs/mbs_evidence_brief.md") or lower.startswith("docs/"):
        return "docs"
    if "/sample_benchmark." in lower or lower.endswith("sample_benchmark.json") or lower.endswith("sample_benchmark.md"):
        return "sample"
    if "evidence_pack_ci" in lower or "/ci_" in lower or lower.endswith("ci_bench.json"):
        return "ci"
    if "fixture" in lower or "/examples/" in lower:
        return "fixture"
    if "provider" in lower or "azure" in lower or "openai" in lower:
        return "provider"
    if "oss" in lower or "hf_" in lower or "huggingface" in lower:
        return "oss"
    if "hpc" in lower or "mn5" in lower or "leonardo" in lower:
        return "hpc"
    if "demo" in lower:
        return "demo"
    return "unknown"


def _findings(path: Path) -> list[str]:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"secret:{label}")
    for label, pattern in SENSITIVE_TEXT_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"sensitive:{label}")
    findings = _suppress_public_contact_findings(path, findings)
    return sorted(set(findings))


def _suppress_public_contact_findings(path: Path, findings: list[str]) -> list[str]:
    if path.name.lower() != "security.md":
        return findings
    return [finding for finding in findings if finding != "sensitive:email"]


def _sensitivity(evidence_class: str, findings: list[str], path: str) -> str:
    if any(item.startswith("secret:") for item in findings):
        return "blocked_secret"
    if any(item.startswith("sensitive:") for item in findings):
        return "restricted_sensitive"
    if evidence_class in PUBLIC_OK_CLASSES:
        return "public"
    if evidence_class in {"provider", "oss", "hpc"}:
        return "restricted_benchmark"
    return "review_required"


def _sharing_boundary(evidence_class: str, sensitivity: str) -> str:
    if sensitivity == "blocked_secret":
        return "Do not share. Remove secrets and regenerate artifact."
    if sensitivity == "restricted_sensitive":
        return "Internal review only until sensitive raw inputs/outputs are redacted."
    if evidence_class in PUBLIC_OK_CLASSES:
        return "May be shared as software/demo evidence, not broad provider benchmark evidence."
    if evidence_class in {"provider", "oss", "hpc"}:
        return "May be shared only after provider/model/run settings and raw-output sensitivity review."
    return "Unclassified; require owner review before external sharing."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify MBS release/evidence artifacts before sharing.")
    parser.add_argument("paths", nargs="+", help="Artifact files or directories to classify.")
    parser.add_argument("--repo-root", default=".", help="Repository root for relative paths.")
    parser.add_argument("--out", help="Optional JSON manifest output path.")
    parser.add_argument("--json", action="store_true", help="Print full JSON manifest.")
    parser.add_argument(
        "--fail-on-review",
        action="store_true",
        help="Exit non-zero when any artifact requires manual review, not only on blocking secrets.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    result = classify_paths([Path(path) for path in args.paths], repo_root=repo_root)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"MBS artifact classification: {result['status']}")
        print(f"- artifacts: {result['artifact_count']}")
        print(f"- review required: {result['review_required_count']}")
        print(f"- blocking findings: {result['blocking_findings_count']}")
    if result["status"] == "FAIL":
        return 2
    if args.fail_on_review and result["status"] == "REVIEW":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
