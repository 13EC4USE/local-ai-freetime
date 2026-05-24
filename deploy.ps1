param(
    [string]$MasterUrl = "http://192.168.1.249:8000",
    [int]$WorkerPort = 9001,
    [string]$WorkerHost = "0.0.0.0",
    [switch]$OpenUi = $true
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvStreamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"

if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}

if (Test-Path $VenvStreamlit) {
    $StreamlitExe = $VenvStreamlit
} else {
    $StreamlitExe = (Get-Command streamlit -ErrorAction Stop).Source
}

function Start-ProjectWindow {
    param(
        [string]$Title,
        [string]$Command
    )

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $Command
    ) -WorkingDirectory $ProjectRoot -WindowStyle Normal | Out-Null

    Write-Host "Started: $Title"
}

Write-Host "Project root: $ProjectRoot"
Write-Host "Python: $PythonExe"
Write-Host "Streamlit: $StreamlitExe"
Write-Host "Master URL: $MasterUrl"
Write-Host "Worker port: $WorkerPort"

$MasterCommand = @"
Set-Location '$ProjectRoot'
`$env:MASTER_URL = '$MasterUrl'
& '$PythonExe' master.py
"@

$WorkerCommand = @"
Set-Location '$ProjectRoot'
`$env:MASTER_URL = '$MasterUrl'
`$env:WORKER_PORT = '$WorkerPort'
`$env:WORKER_HOST = '$WorkerHost'
& '$PythonExe' worker.py
"@

$UiCommand = @"
Set-Location '$ProjectRoot'
& '$StreamlitExe' run ui.py
"@

Start-ProjectWindow -Title "Master" -Command $MasterCommand
Start-ProjectWindow -Title "Worker" -Command $WorkerCommand

if ($OpenUi) {
    Start-ProjectWindow -Title "Streamlit UI" -Command $UiCommand
}

Write-Host ""
Write-Host "All requested services have been launched in separate windows."
Write-Host "If the worker port is busy, run: `n  `$env:WORKER_PORT=9002`n  .\deploy.ps1"
