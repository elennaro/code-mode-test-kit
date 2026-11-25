# The Long session with no pauses: long-session.ps1 -Mode on|off -Folder <run folder with the fixture> [-Last 8]
# Code Mode needs an interactive session (it is not in claude -p), so each turn opens Claude in its own window
# with the turn's prompt (turn 2 on with --continue). A Stop hook (turn-end.py) writes the time the turn ended to
# <folder>.turns; the script then closes that window and starts the next turn at once, so every turn finds the
# 5-minute cache alive. Auto mode as in the first runs, plus an allow list for the tools the task uses, so no
# call waits for a person. Start and end of every turn go to long-session-times.tsv next to this script.
# Needs a clean config ($env:CLAUDE_CONFIG_DIR) and $env:ANTHROPIC_API_KEY, which is never printed.
param(
    [Parameter(Mandatory)][ValidateSet('on', 'off')][string]$Mode,
    [Parameter(Mandatory)][string]$Folder,
    [ValidateRange(1, 8)][int]$Last = 8,
    [string]$Prompts = (Join-Path $PSScriptRoot 'prompts'),
    [ValidateRange(1, 120)][int]$TurnMinutes = 30
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'guard.ps1')
$dir = [IO.Path]::GetFullPath($Folder)
$id = Split-Path -Leaf $dir
Assert-RunFolder $dir
Assert-CleanConfig
if (-not $env:ANTHROPIC_API_KEY) { throw 'Set $env:ANTHROPIC_API_KEY first.' }
foreach ($v in 'ANTHROPIC_MODEL', 'CLAUDE_CODE_EFFORT_LEVEL') {
    if (Test-Path "Env:$v") { throw "Remove `$env:$v first: it overrides the model or effort that plain.json sets." }
}
if (-not (Test-Path -LiteralPath (Join-Path $dir 'tools'))) { throw "Make the fixture first: python fixtures\long-session_genbugs.py $dir" }
$map = Join-Path $PSScriptRoot 'runs-map.tsv'
if ((Test-Path -LiteralPath $map) -and (Select-String -LiteralPath $map -Pattern "^$id`t" -Quiet)) { throw "Run id $id is in runs-map.tsv already." }
$mark = "$dir.turns"
if (Test-Path -LiteralPath $mark) { throw "$mark exists: use a new run folder." }

# plain.json plus the allow list and the Stop hook, written outside the run folder so the model never sees it.
$s = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'plain.json') -Raw | ConvertFrom-Json
$s.permissions | Add-Member allow @('Bash', 'PowerShell', 'REPL', 'Read', 'Glob', 'Grep', 'Edit', 'Write')
$hook = 'python "' + ((Join-Path $PSScriptRoot 'turn-end.py') -replace '\\', '/') + '"'
$s | Add-Member hooks ([pscustomobject]@{ Stop = @([pscustomobject]@{ hooks = @([pscustomobject]@{ type = 'command'; command = $hook }) }) })
$settings = "$dir.settings.json"
$s | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $settings -Encoding ASCII

$times = Join-Path $PSScriptRoot 'long-session-times.tsv'
if (-not (Test-Path -LiteralPath $times)) { Set-Content -LiteralPath $times "id`tmode`tturn`tstart`tend" }
$old = @{}
foreach ($v in 'CLAUDE_CODE_EXPERIMENTAL_CODE_MODE', 'LS_MARK', 'DISABLE_AUTOUPDATER') { $old[$v] = [Environment]::GetEnvironmentVariable($v) }
try {
    if ($Mode -eq 'on') { $env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE = '1' } else { Remove-Item Env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE -ErrorAction SilentlyContinue }
    $env:LS_MARK, $env:DISABLE_AUTOUPDATER = $mark, '1'
    for ($turn = 1; $turn -le $Last; $turn++) {
        $prompt = (Get-Content -LiteralPath (Join-Path $Prompts "long-session-$turn.txt") -Raw -Encoding UTF8).Trim()
        if ($prompt.Contains('"')) { throw "Prompt $turn holds a double quote, which the window's command line would lose." }
        $claudeArgs = @('--settings', "`"$settings`"", '--permission-mode', 'auto')
        if ($turn -gt 1) { $claudeArgs += '--continue' }
        $claudeArgs += "`"$prompt`""
        $start = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        if ($turn -eq 1) { Add-Content -LiteralPath $map "$id`tlong-session`t$Mode`t$start" }
        $p = Start-Process -FilePath claude -ArgumentList $claudeArgs -WorkingDirectory $dir -PassThru
        $deadline = (Get-Date).AddMinutes($TurnMinutes)
        while (@(Get-Content -LiteralPath $mark -ErrorAction SilentlyContinue).Count -lt $turn) {
            if ($p.HasExited) { throw "Claude closed before turn $turn ended." }
            if ((Get-Date) -gt $deadline) { taskkill /T /F /PID $p.Id | Out-Null; throw "Turn $turn ran past $TurnMinutes minutes." }
            Start-Sleep -Seconds 1
        }
        $end = @(Get-Content -LiteralPath $mark)[$turn - 1]
        Start-Sleep -Seconds 3  # let Claude finish writing the log before the window closes
        taskkill /T /F /PID $p.Id | Out-Null
        Add-Content -LiteralPath $times "$id`t$Mode`t$turn`t$start`t$end"
        Write-Host "turn $turn done: $start to $end"
    }
}
finally {
    foreach ($v in $old.Keys) { [Environment]::SetEnvironmentVariable($v, $old[$v]) }
}
