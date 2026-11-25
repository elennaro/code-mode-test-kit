# Checks shared by run.ps1 and decoy.ps1. Dot-source it, then call Assert-RunFolder and, for safety tests,
# Assert-CleanConfig.

function Assert-RunFolder([string]$Path, [switch]$AllowOwnGit) {
    $id = Split-Path -Leaf $Path
    if ($id -notmatch '^[A-Za-z0-9]+$') { throw "Name the run folder with letters and digits only, such as r07; '$id' is not." }
    # No spaces or quotes: the prompts and decoy lists put the path into shell commands unquoted.
    if ($Path -notmatch '^[A-Za-z0-9:\\/._-]+$') { throw 'Use a run folder path of letters, digits and : \ / . _ - only.' }
    if ("$Path\".StartsWith("$PSScriptRoot\", 'OrdinalIgnoreCase')) { throw 'Make the run folder outside this kit.' }
    # Claude Code loads these from the working folder and every parent.
    for ($p = $Path; $p; $p = Split-Path -Parent $p) {
        foreach ($f in 'CLAUDE.md', 'CLAUDE.local.md', '.claude\CLAUDE.md', '.git') {
            if ($AllowOwnGit -and $f -eq '.git' -and $p -eq $Path) { continue }  # hook-check: the fixture is its own small repo
            if (Test-Path -LiteralPath (Join-Path $p $f)) { throw "$p holds $f, so its instructions or files could load into the run. Use a folder outside it." }
        }
    }
}

function Assert-CleanConfig {
    $dir = $env:CLAUDE_CONFIG_DIR
    if (-not $dir) { throw 'Set $env:CLAUDE_CONFIG_DIR to a clean config folder first, so no global rule, plugin or memory takes part.' }
    if ((Resolve-Path -LiteralPath $dir -ErrorAction SilentlyContinue).Path -eq (Join-Path $HOME '.claude')) { throw 'CLAUDE_CONFIG_DIR is your own config: point it at an empty folder.' }
    if (Test-Path -LiteralPath (Join-Path $dir 'CLAUDE.md')) { throw "$dir holds a CLAUDE.md: use a clean config." }
    $file = Join-Path $dir 'settings.json'
    if (Test-Path -LiteralPath $file) {
        $s = Get-Content -LiteralPath $file -Raw | ConvertFrom-Json
        $on = @($s.enabledPlugins.PSObject.Properties | Where-Object { $_.Value -eq $true })
        if ($s.permissions -or $s.hooks -or $on) { throw "$file sets permissions, hooks or plugins: use a clean config." }
    }
}
