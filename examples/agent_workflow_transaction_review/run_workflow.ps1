$ErrorActionPreference = 'Continue'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$Py = if (Test-Path (Join-Path $Root '.audit_venv\Scripts\python.exe')) { Join-Path $Root '.audit_venv\Scripts\python.exe' } else { 'python' }
$OutDir = Join-Path $PSScriptRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$Transcript = Join-Path $OutDir 'workflow_transcript.txt'
"MBS agent workflow transaction review`nStarted: $(Get-Date -Format o)`n" | Set-Content -Path $Transcript -Encoding UTF8
function Run-Step($Name, $Command, $Allowed = @(0)) {
  "`n## $Name`n> $Command" | Add-Content -Path $Transcript -Encoding UTF8
  $output = & powershell -NoProfile -ExecutionPolicy Bypass -Command $Command 2>&1
  $exit = $LASTEXITCODE
  $output | Add-Content -Path $Transcript -Encoding UTF8
  "EXIT=$exit" | Add-Content -Path $Transcript -Encoding UTF8
  if ($Allowed -notcontains $exit) { throw "Step '$Name' failed with exit $exit" }
}
Run-Step 'validate good candidate' "Set-Location '$Root'; & '$Py' -m mbs.cli validate --schema examples/agent_workflow_transaction_review/schema.json --output examples/agent_workflow_transaction_review/candidate_good.json --json | Tee-Object -FilePath '$OutDir\validate_good.json'"
Run-Step 'validate bad candidate' "Set-Location '$Root'; & '$Py' -m mbs.cli validate --schema examples/agent_workflow_transaction_review/schema.json --output examples/agent_workflow_transaction_review/candidate_bad.json --json | Tee-Object -FilePath '$OutDir\validate_bad.json'" @(1,2)
Run-Step 'check good candidate and trace' "Set-Location '$Root'; & '$Py' -m mbs.cli check --schema examples/agent_workflow_transaction_review/schema.json --input 'Transaction TXN-41002: 4800 EUR to a new beneficiary. Known device. Normal account history.' --output examples/agent_workflow_transaction_review/candidate_good.json --model transaction-review-agent --trace-out '$OutDir\trace_good.json' --json | Tee-Object -FilePath '$OutDir\check_good.json'"
Run-Step 'agent tool good request' "Set-Location '$Root'; & '$Py' -m mbs.cli agent-tools --request examples/agent_workflow_transaction_review/agent_tool_request_good.json --json | Tee-Object -FilePath '$OutDir\agent_tool_good.json'"
Run-Step 'agent tool bad request' "Set-Location '$Root'; & '$Py' -m mbs.cli agent-tools --request examples/agent_workflow_transaction_review/agent_tool_request_bad.json --json | Tee-Object -FilePath '$OutDir\agent_tool_bad.json'"
"`nCompleted: $(Get-Date -Format o)" | Add-Content -Path $Transcript -Encoding UTF8
Write-Host "Workflow artifacts written to $OutDir"
