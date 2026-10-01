# Publishes pytest coverage into the SonarQube web UI at http://localhost:9000
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$sonarUrl = "http://localhost:9000"
$adminUser = "admin"
$labPassword = "Admin12345!!!"
$tokenFile = Join-Path $root ".sonar-token"
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

function New-BasicAuth([string]$user, [string]$password) {
    $bytes = [Text.Encoding]::ASCII.GetBytes("${user}:${password}")
    return @{ Authorization = "Basic " + [Convert]::ToBase64String($bytes) }
}

function Test-SonarAuth($headers) {
    try {
        Invoke-RestMethod -Uri "$sonarUrl/api/user_tokens/search" -Headers $headers | Out-Null
        return $true
    } catch {
        return $false
    }
}

$auth = New-BasicAuth $adminUser $labPassword
if (-not (Test-SonarAuth $auth)) {
    $bootstrap = New-BasicAuth $adminUser "admin"
    if (-not (Test-SonarAuth $bootstrap)) {
        throw "Cannot log in to SonarQube. Open $sonarUrl and sign in as admin."
    }
    try {
        Invoke-RestMethod -Method Post -Uri "$sonarUrl/api/users/change_password" `
            -Headers $bootstrap `
            -ContentType "application/x-www-form-urlencoded" `
            -Body @{
                login            = $adminUser
                previousPassword = "admin"
                password         = $labPassword
            } | Out-Null
        $auth = New-BasicAuth $adminUser $labPassword
        if (-not (Test-SonarAuth $auth)) { throw "new password rejected" }
    } catch {
        Write-Host "Keeping default SonarQube password admin/admin"
        $labPassword = "admin"
        $auth = $bootstrap
    }
}

try {
    Invoke-RestMethod -Method Post -Uri "$sonarUrl/api/user_tokens/revoke" -Headers $auth -Body @{ name = "wildlife-local" } | Out-Null
} catch { }
$created = Invoke-RestMethod -Method Post -Uri "$sonarUrl/api/user_tokens/generate" -Headers $auth -Body @{
    name = "wildlife-local"
}
$token = $created.token
Set-Content -Path $tokenFile -Value $token -Encoding ascii

Write-Host "Running tests and writing coverage.xml / htmlcov..."
py -m pytest | Out-Host

$env:SONAR_TOKEN = $token
Write-Host "Uploading coverage to SonarQube..."
docker compose --profile scan run --rm -e "SONAR_TOKEN=$token" scanner | Out-Host

$dashboard = "$sonarUrl/dashboard?id=$projectKey"
$htmlReport = Join-Path $root "htmlcov\index.html"
Write-Host "Coverage UI: $dashboard"
Write-Host "Login: $adminUser / $labPassword"
Write-Host "Local HTML report: $htmlReport"
try { Start-Process $dashboard } catch { }
try { Start-Process $htmlReport } catch { }
