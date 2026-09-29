param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^(?:[01]\d|2[0-3]):[0-5]\d$')]
    [string] $At,
    [string] $PythonPath
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
if (-not $PythonPath) {
    $localVenvPython = Join-Path $repoRoot '.ri-ops-venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $localVenvPython) {
        $PythonPath = $localVenvPython
    } else {
        $PythonPath = (Get-Command python.exe -ErrorAction Stop).Source
    }
}
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'scripts\intelligence\cli.py'))) {
    throw 'Repository root does not contain the Research Intelligence CLI.'
}

$taskName = 'BubblevanResearchIntelligenceDaily'
$timeOfDay = [datetime]::ParseExact($At, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument '-m scripts.intelligence.cli intelligence-daily --mode production --scheduled' `
    -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $timeOfDay
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal `
    -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType S4U `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'Runs the local Research Intelligence daily pipeline. No credentials are stored in the task.' `
    -Force | Out-Null

Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State, @{n='Action';e={$_.Actions.Execute}}, @{n='Arguments';e={$_.Actions.Arguments}}, @{n='WorkingDirectory';e={$_.Actions.WorkingDirectory}}
