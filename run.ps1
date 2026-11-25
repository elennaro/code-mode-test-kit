# Start one test run in the current folder: run.ps1 -Mode on|off -Test <test> [-Turn <n>] [-Subscription]
# The prompt is prompts\<test>.txt, word for word as the original runs got it, with no tag. Placeholders:
# {RUN_ID} and {RUN_FOLDER} come from the run folder, {FIGMA_FILE_KEY} from $env:FIGMA_FILE_KEY.
# The run is named after its folder (a neutral id such as r07); runs-map.tsv next to this script records which
# test and mode that id was. The API key comes from $env:ANTHROPIC_API_KEY and is never printed or written.
# -Subscription uses the claude.ai login instead (tests docs and figma). -Turn 2 to 8 continues the long session.
# The terminal's environment is put back as it was when Claude exits.
param(
    [Parameter(Mandatory)][ValidateSet('on', 'off')][string]$Mode,
    [Parameter(Mandatory)][string]$Test,
    [ValidateRange(1, 8)][int]$Turn = 1,
    [switch]$Subscription
)
$ErrorActionPreference = 'Stop'
$inProject = (Split-Path -Leaf $PWD) -eq 'project'
$outsideTest = $Test -in 'safety-outside', 'safety-deny-outside'
if ($outsideTest -ne $inProject) { throw 'Only safety-outside and safety-deny-outside run in <run folder>\project, and they run nowhere else.' }
# The deny rule tests run in default mode with every tool allowed (allow.json), so only the folder's deny rules
# decide. Every other test runs in auto mode (plain.json), as all the first runs did.
$ruleTest = $Test -like 'safety-deny-*'
. (Join-Path $PSScriptRoot 'guard.ps1')
if ($Test -like 'safety-*') {
    Assert-CleanConfig
    # The folder must hold deny rules exactly when the test name says so, or a run gets the wrong label.
    if ($ruleTest -ne (Test-Path -LiteralPath '.claude\settings.json')) { throw "This folder's rules do not fit ${Test}: make it with safety_setup.py and the matching test." }
}
$dir = if ($inProject) { Split-Path -Parent $PWD } else { "$PWD" }
$id = Split-Path -Leaf $dir
$map = Join-Path $PSScriptRoot 'runs-map.tsv'
$name = if ($Test -eq 'long-session') { "long-session-$Turn" } else { $Test }
$file = Join-Path $PSScriptRoot "prompts\$name.txt"

if (-not (Test-Path -LiteralPath $file)) {
    $tests = (Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'prompts') -Filter *.txt).BaseName -replace '^long-session-\d$', 'long-session' | Sort-Object -Unique
    throw "No prompt for test '$Test'. Tests: $($tests -join ', ')"
}
Assert-RunFolder $dir
foreach ($v in 'ANTHROPIC_MODEL', 'CLAUDE_CODE_EFFORT_LEVEL') {
    if (Test-Path "Env:$v") { throw "Remove `$env:$v first: it overrides the model or effort that plain.json sets." }
}
$continue = $Turn -gt 1
if ($continue -and $Test -ne 'long-session') { throw '-Turn is only for the long-session test.' }
$known = @(if (Test-Path -LiteralPath $map) { Get-Content -LiteralPath $map | Where-Object { ($_ -split "`t")[0] -eq $id } })
if (-not $continue -and $known) { throw "Run id $id is in runs-map.tsv already: use a new folder and id." }
if ($continue -and -not ($known | Where-Object { $_ -like "$id`tlong-session`t$Mode`t*" })) {
    throw "runs-map.tsv has no long-session turn 1 for $id in mode ${Mode}: start it with -Turn 1."
}

$prompt = (Get-Content -LiteralPath $file -Raw -Encoding UTF8).Trim().Replace('{RUN_ID}', $id).Replace('{RUN_FOLDER}', ($dir -replace '\\', '/'))
if ($prompt.Contains('{FIGMA_FILE_KEY}')) {
    if (-not $env:FIGMA_FILE_KEY) { throw 'Set $env:FIGMA_FILE_KEY to the key of your Figma file first.' }
    $prompt = $prompt.Replace('{FIGMA_FILE_KEY}', $env:FIGMA_FILE_KEY)
}

$oldKey, $oldMode = $env:ANTHROPIC_API_KEY, $env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE
try {
    if ($Subscription) { Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue }
    elseif (-not $env:ANTHROPIC_API_KEY) { throw 'Set $env:ANTHROPIC_API_KEY first, or pass -Subscription.' }
    if ($Mode -eq 'on') { $env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE = '1' } else { Remove-Item Env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE -ErrorAction SilentlyContinue }
    if (-not $continue) { Add-Content -LiteralPath $map "$id`t$Test`t$Mode`t$((Get-Date).ToUniversalTime().ToString('s'))Z" }
    $settings = Join-Path $PSScriptRoot $(if ($ruleTest) { 'allow.json' } else { 'plain.json' })
    $permission = if ($ruleTest) { 'default' } else { 'auto' }
    if ($continue) { claude --settings $settings --permission-mode $permission --continue $prompt }
    else { claude --settings $settings --permission-mode $permission $prompt }
}
finally {
    $env:ANTHROPIC_API_KEY, $env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE = $oldKey, $oldMode
}
