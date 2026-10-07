# Publishes pytest coverage into the SonarQube web UI at http://localhost:9000
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$sonarUrl = "http://localhost:9000"
$projectKey = "wildlife-monitoring"

Write-Host "Starting SonarQube..."
docker compose up -d sonarqube | Out-Host

function Get-SonarStatus {
    try {
        return (Invoke-RestMethod -Uri "$sonarUrl/api/system/status" -TimeoutSec 5).status
    } catch {
        return $null
    }
}

Write-Host "Waiting for SonarQube at $sonarUrl ..."
$deadline = (Get-Date).AddMinutes(8)
do {
    $status = Get-SonarStatus
    if ($status -eq "UP") { break }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)

if ($status -ne "UP") {
    throw "SonarQube did not become UP in time. Last status: $status"
}

Write-Host "Running tests and writing coverage.xml / htmlcov..."
py -m pytest | Out-Host

Write-Host "Uploading coverage to SonarQube..."
docker compose --profile scan run --rm scanner | Out-Host

$dashboard = "$sonarUrl/dashboard?id=$projectKey"
$htmlReport = Join-Path $root "htmlcov\index.html"
Write-Host "Coverage UI: $dashboard"
Write-Host "Local HTML report: $htmlReport"
try { Start-Process $dashboard } catch { }
try { Start-Process $htmlReport } catch { }
