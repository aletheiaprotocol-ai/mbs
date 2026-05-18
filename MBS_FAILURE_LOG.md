# MBS Failure Log

## Findings during May 2026 Product Readiness Audit

### 1. UTF-8 BOM Output JSON Crash (FIXED)

**Severity:** High - CLI crashes instead of returning validation failure

**Discovery Date:** May 16, 2026

**Root Cause:** Windows PowerShell writes JSON files with UTF-8 BOM prefix by default. The MBS CLI output JSON loader (`_load_json_or_inline` in `mbs/cli.py`) was reading files with `encoding="utf-8"`, which does not strip the BOM character. When a user created an output JSON file from PowerShell and passed it to `mbs validate`, the CLI crashed with:

```
json.decoder.JSONDecodeError: Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)
```

**Impact:**
- MBS `validate` command cannot accept user-created output files from Windows PowerShell
- MBS `check` command cannot accept user-provided output files from Windows PowerShell
- Affects Windows users creating test scripts or automating validation

**Reproduction Steps:**
```powershell
# Create output JSON from PowerShell (results in UTF-8 BOM encoding)
$output | Out-File -Encoding UTF8 output.json

# Try to validate - crashes
python -m mbs.cli validate --schema schema.json --output output.json
# Error: json.decoder.JSONDecodeError: Unexpected UTF-8 BOM
```

**Test Coverage Before Fix:**
- Schema loading supported BOM (added in earlier audit fix)
- Output JSON loading did NOT support BOM (this bug)

---

## Files Involved

### Entry Point
- `mbs/cli.py` - `_load_json_or_inline()` function

### Test Coverage
- `tests/test_mbs_conformance.py` - `test_cli_validate_supports_output_json_files_with_utf8_bom()`

---

### 2. Malformed JSON Output File Traceback (FIXED)

**Severity:** Medium - CLI returns a traceback for syntactically invalid file-backed JSON

**Discovery Date:** May 16, 2026

**Status:** Fixed in the May 17, 2026 P0 productization slice.

**Observed Behavior:** A malformed output JSON file such as `{"decision":` still raises `json.decoder.JSONDecodeError` from `_load_json_or_inline()` because existing helper behavior only converts invalid inline JSON strings into raw strings; it does not catch `JSONDecodeError` for existing files.

**Boundary:** This is separate from the UTF-8 BOM bug. The BOM-prefixed but syntactically valid output file now returns a controlled MBS validation failure instead of a traceback.

**Resolution:** File-backed JSON parse failures in covered CLI paths now return a short controlled `MBS input error` without traceback. Regression coverage includes invalid JSON files and routine file/path mistakes.

---

### 3. PowerShell JSON artifact encoding caveat (OPEN)

**Severity:** Low/Medium - generated audit transcript files may be unreadable by UTF-8-only tooling if written by PowerShell redirection or `Tee-Object` defaults.

**Discovery Date:** May 17, 2026

**Observed Behavior:** CLI stdout JSON is valid, but files captured through some PowerShell redirection paths can be UTF-16 or BOM-encoded. Pytest attempted to collect a generated `test_help.txt` artifact and failed with a UTF-8 decode error before the artifact was renamed out of pytest's collection pattern.

**Impact:** Not an MBS JSON contract failure, but a Windows evidence/artifact hygiene issue for local audit files.

**Follow-up:** Ensure generated evidence files use explicit UTF-8 capture and avoid names matching pytest collection patterns.

---

## Status

**BOM output JSON crash fixed** - See MBS_FIX_LOG.md for implementation details. Malformed file-backed JSON traceback remains a documented hardening task.
