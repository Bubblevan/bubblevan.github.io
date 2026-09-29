$ErrorActionPreference = 'Stop'
$taskName = 'BubblevanResearchIntelligenceDaily'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    [pscustomobject]@{ TaskName = $taskName; Installed = $false }
    exit 0
}
$info = Get-ScheduledTaskInfo -TaskName $taskName
[pscustomobject]@{
    TaskName = $taskName
    Installed = $true
    State = $task.State
    Execute = $task.Actions.Execute
    Arguments = $task.Actions.Arguments
    WorkingDirectory = $task.Actions.WorkingDirectory
    StartWhenAvailable = $task.Settings.StartWhenAvailable
    RunOnlyIfNetworkAvailable = $task.Settings.RunOnlyIfNetworkAvailable
    MultipleInstances = $task.Settings.MultipleInstances
    ExecutionTimeLimit = $task.Settings.ExecutionTimeLimit
    LastRunTime = $info.LastRunTime
    NextRunTime = $info.NextRunTime
    LastTaskResult = $info.LastTaskResult
} | Format-List
