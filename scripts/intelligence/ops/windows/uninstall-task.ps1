$ErrorActionPreference = 'Stop'
$taskName = 'BubblevanResearchIntelligenceDaily'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    'Uninstalled ' + $taskName
} else {
    'Task is not installed: ' + $taskName
}
