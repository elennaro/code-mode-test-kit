# One run with no pauses: auto-run.ps1 -Test <test> -Mode on|off -Folder <run folder with its fixture> [-Subscription]
# Code Mode needs an interactive session (it is not in claude -p), so each turn opens Claude in its own window
# with the turn's prompt (later turns of the long session with --continue). A Stop hook (turn-end.py) writes the
# time the turn ended to <folder>.turns; the script then closes that window and, in the long session, starts the
# next turn at once, so every turn finds the cache alive. Auto mode as in the first runs, plus an allow list for
# the tools the tests use, so no call waits for a person. Start and end of every turn go to auto-run-times.tsv,
# and the run to runs-map.tsv, both next to this script.
# Needs a clean config ($env:CLAUDE_CONFIG_DIR). $env:ANTHROPIC_API_KEY is used and never printed; -Subscription
# clears it for the run and uses the config's claude.ai login (the docs and figma tests).
param(
    [Parameter(Mandatory)][string]$Test,
    [Parameter(Mandatory)][ValidateSet('on', 'off')][string]$Mode,
    [Parameter(Mandatory)][string]$Folder,
    [switch]$Subscription,
    [switch]$NoAllow,  # no allow list: every call goes to the auto mode check, as in the first set
    [ValidateRange(1, 8)][int]$Last = 8,
    [string]$Prompts = (Join-Path $PSScriptRoot 'prompts'),
    [ValidateRange(1, 120)][int]$TurnMinutes = 30
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'guard.ps1')
$dir = [IO.Path]::GetFullPath($Folder)
$id = Split-Path -Leaf $dir
Assert-RunFolder $dir -AllowOwnGit:($Test -eq 'hook-check')
Assert-CleanConfig
# A claude.ai login syncs the account's plugins and skills into the config, and they load even on the API key.
if (-not $Subscription -and ((Test-Path -LiteralPath "$env:CLAUDE_CONFIG_DIR\plugins\synced") -or
        (Select-String -LiteralPath "$env:CLAUDE_CONFIG_DIR\.claude.json" -Pattern '"oauthAccount"' -Quiet))) {
    throw "$env:CLAUDE_CONFIG_DIR has a claude.ai login or synced plugins: use a config without them for API key runs."
}
if (-not $Subscription -and -not $env:ANTHROPIC_API_KEY) { throw 'Set $env:ANTHROPIC_API_KEY first, or pass -Subscription.' }
foreach ($v in 'ANTHROPIC_MODEL', 'CLAUDE_CODE_EFFORT_LEVEL') {
    if (Test-Path "Env:$v") { throw "Remove `$env:$v first: it overrides the model or effort that plain.json sets." }
}
if (-not (Test-Path -LiteralPath $dir)) { throw "Make the run folder and its fixture first." }
$names = if ($Test -eq 'long-session') { 1..$Last | ForEach-Object { "long-session-$_" } } else { , $Test }
$turns = foreach ($n in $names) {
    $file = Join-Path $Prompts "$n.txt"
    if (-not (Test-Path -LiteralPath $file)) { throw "No prompt $file." }
    $p = (Get-Content -LiteralPath $file -Raw -Encoding UTF8).Trim().Replace('{RUN_ID}', $id).Replace('{RUN_FOLDER}', ($dir -replace '\\', '/'))
    if ($p.Contains('{FIGMA_FILE_KEY}')) {
        if (-not $env:FIGMA_FILE_KEY) { throw 'Set $env:FIGMA_FILE_KEY to the key of your Figma file first.' }
        $p = $p.Replace('{FIGMA_FILE_KEY}', $env:FIGMA_FILE_KEY)
    }
    if ($p.Contains('"')) { throw "Prompt $n holds a double quote, which the window's command line would lose." }
    $p
}
$map = Join-Path $PSScriptRoot 'runs-map.tsv'
if ((Test-Path -LiteralPath $map) -and (Select-String -LiteralPath $map -Pattern "^$id`t" -Quiet)) { throw "Run id $id is in runs-map.tsv already." }
$mark = "$dir.turns"
if (Test-Path -LiteralPath $mark) { throw "$mark exists: use a new run folder." }

# plain.json plus the allow list and the Stop hook, written outside the run folder so the model never sees it.
$s = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'plain.json') -Raw | ConvertFrom-Json
if (-not $NoAllow) {
    $s.permissions | Add-Member allow @('Bash', 'PowerShell', 'REPL', 'Read', 'Glob', 'Grep', 'Edit', 'Write',
        'mcp__claude_ai_Claude_Docs', 'mcp__claude_ai_figma-mcp')
}
$hook = 'python "' + ((Join-Path $PSScriptRoot 'turn-end.py') -replace '\\', '/') + '"'
$hooks = [pscustomobject]@{ Stop = @([pscustomobject]@{ hooks = @([pscustomobject]@{ type = 'command'; command = $hook }) }) }
if ($Test -eq 'hook-check') {  # Test 2: a PreToolUse hook on every tool writes one line per call to <folder>.hooks.txt
    $log = 'python "' + ((Join-Path $PSScriptRoot 'hook-log.py') -replace '\\', '/') + '"'
    $hooks | Add-Member PreToolUse @([pscustomobject]@{ matcher = '*'; hooks = @([pscustomobject]@{ type = 'command'; command = $log }) })
}
$s | Add-Member hooks $hooks
$settings = "$dir.settings.json"
$s | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $settings -Encoding ASCII

$times = Join-Path $PSScriptRoot 'auto-run-times.tsv'
if (-not (Test-Path -LiteralPath $times)) { Set-Content -LiteralPath $times "id`ttest`tmode`tturn`tstart`tend" }
$old = @{}
foreach ($v in 'CLAUDE_CODE_EXPERIMENTAL_CODE_MODE', 'LS_MARK', 'DISABLE_AUTOUPDATER', 'ANTHROPIC_API_KEY') { $old[$v] = [Environment]::GetEnvironmentVariable($v) }
try {
    if ($Mode -eq 'on') { $env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE = '1' } else { Remove-Item Env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE -ErrorAction SilentlyContinue }
    if ($Subscription) { Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue }
    $env:LS_MARK, $env:DISABLE_AUTOUPDATER = $mark, '1'
    for ($turn = 1; $turn -le @($turns).Count; $turn++) {
        $claudeArgs = @('--settings', "`"$settings`"", '--permission-mode', 'auto')
        if ($turn -gt 1) { $claudeArgs += '--continue' }
        $claudeArgs += "`"$(@($turns)[$turn - 1])`""
        $start = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        if ($turn -eq 1) { Add-Content -LiteralPath $map "$id`t$Test`t$Mode`t$start" }
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
        Add-Content -LiteralPath $times "$id`t$Test`t$Mode`t$turn`t$start`t$end"
        Write-Host "$id $Test $Mode turn $turn done: $start to $end"
    }
}
finally {
    foreach ($v in $old.Keys) { [Environment]::SetEnvironmentVariable($v, $old[$v]) }
}
