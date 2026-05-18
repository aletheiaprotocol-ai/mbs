from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "mbs_cli_command_matrix_20260517.md"

PUBLIC_SUBCOMMANDS = [
    "compile",
    "validate",
    "check",
    "trace",
    "cost",
    "bench",
    "demo",
    "test",
    "lang",
    "report",
    "gate",
    "evidence-pack",
    "compare",
    "retry-audit",
    "models",
    "triage",
    "agent-tools",
    "adapt-responses",
    "make-response-template",
]


def test_cli_command_matrix_doc_tracks_public_subcommands_and_boundaries():
    text = DOC.read_text(encoding="utf-8")

    for command in PUBLIC_SUBCOMMANDS:
        assert f"`{command}`" in text
        assert f"{command}|exit=0" in text

    assert "Remote non-Windows CI evidence remains a separate blocker" in text
    assert "test_cli_edge_command_matrix_returns_controlled_errors" in text
    assert "test_cli_artifact_commands_accept_bom_encoded_inputs" in text
