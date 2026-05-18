# Expected outputs

This smoke test proves a fresh external user can:

- create a clean virtual environment
- install the local MBS package
- verify imports resolve to this repository
- compile a workflow schema
- validate a valid output with exit code 0
- validate an invalid output with a nonzero exit code and machine-readable failure JSON
- run `check` with the mock model and create a trace file
- list JSON-callable agent tools
- call the validation agent tool with JSON arguments

Required artifacts are written under `external_user_smoke_test/artifacts/` and every command/exit code is logged in `command_transcript.txt`.
