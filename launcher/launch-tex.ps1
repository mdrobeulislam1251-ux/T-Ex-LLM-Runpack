# T-Ex LLM launcher — portable: resolves everything relative to this file's location.
# Works from any drive or folder; never hardcode a path in this file.
$ErrorActionPreference = 'Stop'

$TexHome = Join-Path $PSScriptRoot '.claude-tex'
if (-not (Test-Path (Join-Path $TexHome 'CLAUDE.md'))) {
    Write-Host "[T-Ex] ERROR: .claude-tex home not found next to launcher ($TexHome)" -ForegroundColor Red
    exit 1
}

$env:CLAUDE_CONFIG_DIR = $TexHome
Write-Host "[T-Ex] Config home: $TexHome" -ForegroundColor Cyan

# Launch in the directory the user invoked from (their project), passing through any args.
claude @args
