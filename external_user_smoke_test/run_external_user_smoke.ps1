$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
$TranscriptPath = Join-Path $PSScriptRoot 'command_transcript.txt'
$ExpectedPath = Join-Path $PSScriptRoot 'expected_outputs.md'
$Artifacts = Join-Path $PSScriptRoot 'artifacts'
$Venv = Join-Path $PSScriptRoot '.venv_smoke'
New-Item -ItemType Directory -Force -Path $Artifacts | Out-Null
$InvalidOutputPath = Join-Path $Artifacts 'invalid_output.json'
$AgentArgsPath = Join-Path $Artifacts 'agent_validate_args.json'
$ValidOutputPath = Join-Path $Root 'examples\fintech_transaction_risk\output.json'
$ValidOutputJson = (Get-Content -Raw -Path $ValidOutputPath)
@'
{"schema_version":"fintech_transaction_risk.v1","risk_level":"CRITICAL","decision":"ALLOW"}
'@ | Set-Content -Path $InvalidOutputPath -Encoding UTF8
@'
{
    "schema_path": "examples/fintech_transaction_risk/schema.json",
    "output": __OUTPUT__
}
'@ | Set-Content -Path $AgentArgsPath -Encoding UTF8
(Get-Content -Raw -Path $AgentArgsPath).Replace('__OUTPUT__', $ValidOutputJson) | Set-Content -Path $AgentArgsPath -Encoding UTF8
"MBS external-user smoke test transcript`nRoot: $Root`nStarted: $(Get-Date -Format o)`n" | Set-Content -Path $TranscriptPath -Encoding UTF8

function Run-Step {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$Command,
        [int[]]$AllowedExitCodes = @(0)
    )
    "`n## $Name`n> $Command" | Add-Content -Path $TranscriptPath -Encoding UTF8
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -Command $Command 2>&1
    $exit = $LASTEXITCODE
    $output | Add-Content -Path $TranscriptPath -Encoding UTF8
    "EXIT=$exit" | Add-Content -Path $TranscriptPath -Encoding UTF8
    if ($AllowedExitCodes -notcontains $exit) {
        throw "Step '$Name' failed with exit code $exit"
    }
}

if (!(Test-Path $Venv)) {
    Run-Step 'create fresh venv' "py -3.11 -m venv '$Venv'"
}
Run-Step 'upgrade pip' "& '$Venv\Scripts\python.exe' -m pip install --upgrade pip"
Run-Step 'install mbs package' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -m pip install -e ."
Run-Step 'verify import path' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -c 'import pathlib, mbs, mbs.cli; print(pathlib.Path(mbs.__file__).resolve()); print(pathlib.Path(mbs.cli.__file__).resolve())'"
Run-Step 'compile schema json' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -m mbs.cli compile examples/fintech_transaction_risk/schema.json --json | Tee-Object -FilePath '$Artifacts\compile.json'"
Run-Step 'validate valid output json' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output examples/fintech_transaction_risk/output.json --json | Tee-Object -FilePath '$Artifacts\validate_valid.json'"
Run-Step 'validate invalid output json' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -m mbs.cli validate --schema examples/fintech_transaction_risk/schema.json --output '$InvalidOutputPath' --json | Tee-Object -FilePath '$Artifacts\validate_invalid.json'" @(1, 2)
Run-Step 'run check mock and trace' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -m mbs.cli check --schema examples/fintech_transaction_risk/schema.json --input 'Customer transfers 4800 EUR to a new beneficiary' --output '$ValidOutputPath' --model mock --trace-out '$Artifacts\trace.json' --json | Tee-Object -FilePath '$Artifacts\check_mock.json'"
Run-Step 'list agent tools json' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -m mbs.cli agent-tools --list --json | Tee-Object -FilePath '$Artifacts\agent_tools.json'"
Run-Step 'call agent validation tool' "Set-Location '$Root'; & '$Venv\Scripts\python.exe' -m mbs.cli agent-tools --call mbs.validate --args '$AgentArgsPath' --json | Tee-Object -FilePath '$Artifacts\agent_validate.json'"

@'
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
'@ | Set-Content -Path $ExpectedPath -Encoding UTF8
"`nCompleted: $(Get-Date -Format o)" | Add-Content -Path $TranscriptPath -Encoding UTF8
Write-Host "Smoke test passed. Transcript: $TranscriptPath"
