# The terminal session that the demo video records.
#
# Every command is typed at the real PowerShell prompt by this script and then
# run for real. demo/record_screen.py opens the window, records it, and uses the
# timestamps written here to cut the footage.
param(
    [string]$Rec = "demo/out/rec",
    [switch]$Test
)

$ErrorActionPreference = "Continue"
$env:PYTHONUNBUFFERED = "1"
# The recorder may run inside another tool's virtualenv; the session must not inherit it.
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$MarksFile = Join-Path $Rec "marks.jsonl"
$Source = ".cache/demo-source"
$Twin = ".cache/demo-twin"
$Page = "docs/provider-capabilities.md"

function Mark([string]$Name) {
    $ms = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    Add-Content -Path $MarksFile -Value ("{""name"": ""$Name"", ""ms"": $ms}") -Encoding ascii
}

function Wait-For([string]$Name, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while (-not (Test-Path (Join-Path $Rec $Name))) {
        if ((Get-Date) -gt $deadline) { return $false }
        Start-Sleep -Milliseconds 100
    }
    return $true
}

function Show-Prompt { Write-Host -NoNewline (prompt) }

# Type a command at the prompt that is already on screen, run it, show the next prompt.
function Step([string]$Name, [string]$Command, [int]$After = 1500) {
    Mark "$Name.prompt"
    Start-Sleep -Milliseconds 700
    foreach ($ch in $Command.ToCharArray()) {
        Write-Host -NoNewline $ch
        Start-Sleep -Milliseconds 12
    }
    Start-Sleep -Milliseconds 350
    Write-Host ""
    Mark "$Name.typed"
    Invoke-Expression $Command
    Mark "$Name.done"
    Show-Prompt
    Start-Sleep -Milliseconds $After
}

function Clear-Screen { Clear-Host; Show-Prompt }

Write-Host "DocTwin demo session. Waiting for the screen recorder ..."
if ($Test) {
    Write-Host ("1234567890" * 13)
    1..40 | ForEach-Object { Write-Host ("row {0:d2}  docs/provider-capabilities.md: 5 sections, 1 to translate, 0 to re-review, 4 reused" -f $_) }
    Show-Prompt
    Wait-For "stop" 20 | Out-Null
    exit 0
}
if (-not (Wait-For "go" 60)) { exit 3 }

Clear-Screen
Mark "start"
Start-Sleep -Milliseconds 1000

# 1. What would a sync send to the model?
Step "plan" "uv run doctwin plan --source $Source --out $Twin" 2000

# 2. The sync itself: translator agent, gates, reviewer subagent, DocDrift validation.
Step "sync" "uv run doctwin sync --source $Source --out $Twin --terms yes" 3000

# 3. What it wrote, against the committed translation.
Clear-Screen
Step "diff" "git --no-pager diff --no-index --word-diff=color -U1 translations/id/$Page $Twin/$Page" 3500

# 4. Approval gate: one glossary term approved, one denied.
Clear-Screen
Step "glossary" "uv run python demo/glossary_approval.py $Twin" 3000

# 5. A person edits the translation; the next sync must leave that file alone.
Clear-Screen
Step "edit" "Add-Content $Twin/$Page ""Catatan dari editor manusia.""" 600
Step "resync" "uv run doctwin sync --source $Source --out $Twin --terms skip --no-validate" 3000

Mark "end"
Wait-For "stop" 30 | Out-Null
$Host.UI.RawUI.FlushInputBuffer()
exit 0
