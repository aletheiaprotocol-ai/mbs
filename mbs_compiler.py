"""Backward-compatible import shim for the original MBS compiler module."""

from __future__ import annotations

import sys

from mbs.cli import main as _mbs_main
from mbs.compiler import classify_enum, compile_schema, extract_fields, format_report, load_schema

__all__ = [
    "classify_enum",
    "compile_schema",
    "extract_fields",
    "format_report",
    "load_schema",
    "main",
]


def main(argv: list[str] | None = None) -> int:
    """Preserve old `mbs-compile schema.json` behavior."""
    args = list(sys.argv[1:] if argv is None else argv)
    commands = {"compile", "validate", "check", "trace", "cost", "bench", "test", "lang"}
    if not args or args[0] not in commands:
        args = ["compile", *args]
    return _mbs_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
