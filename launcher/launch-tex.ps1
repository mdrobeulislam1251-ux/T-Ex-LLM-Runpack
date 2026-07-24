# T-Ex LLM launcher — portable standalone mode: one T-Ex agent carrying the full
# runpack skill set. Resolves everything relative to this file's location; never
# hardcode a path in this file.
$ErrorActionPreference = 'Stop'

$TexHome = Join-Path $PSScriptRoot '.claude-tex'
if (-not (Test-Path (Join-Path $TexHome 'CLAUDE.md'))) {
    Write-Host "[T-Ex] ERROR: .claude-tex home not found next to launcher ($TexHome)" -ForegroundColor Red
    exit 1
}

# Skills live ONCE in the runpack (plugins/tex-llm/skills — single source of truth).
# Mirror them into the standalone home on every launch so both modes never drift.
$SkillsSrc = Join-Path (Split-Path $PSScriptRoot -Parent) 'plugins\tex-llm\skills'
$SkillsDst = Join-Path $TexHome 'skills'
if (Test-Path $SkillsSrc) {
    robocopy $SkillsSrc $SkillsDst /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    Write-Host "[T-Ex] Skills synced from runpack: $SkillsSrc" -ForegroundColor DarkGray
} elseif (-not (Test-Path $SkillsDst)) {
    Write-Host "[T-Ex] ERROR: runpack skills not found at $SkillsSrc and no local skills/ present" -ForegroundColor Red
    exit 1
}

$env:CLAUDE_CONFIG_DIR = $TexHome
Write-Host "[T-Ex] Config home: $TexHome" -ForegroundColor Cyan

# Launch in the directory the user invoked from (their project), passing through any args.
claude @args
