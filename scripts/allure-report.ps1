# Runs pytest and opens the Allure report in a local server window.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$allureVersion = "2.46.1"
$results = Join-Path $root "allure-results"
$report = Join-Path $root "allure-report"

Write-Host "Running tests and writing $results ..."
py -m pytest
$pytestCode = $LASTEXITCODE

function Find-AllureBat {
    $tools = Join-Path $root "tools"
    if (Test-Path $tools) {
        $bundled = Get-ChildItem $tools -Filter "allure.bat" -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\bin\\allure\.bat$' } |
            Select-Object -First 1
        if ($bundled) { return $bundled.FullName }
    }

    foreach ($name in @("allure.bat", "allure.cmd")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

function Install-AllureCli {
    $url = "https://github.com/allure-framework/allure2/releases/download/$allureVersion/allure-$allureVersion.zip"
    $zip = Join-Path $env:TEMP "allure-$allureVersion.zip"
    $tools = Join-Path $root "tools"
    New-Item -ItemType Directory -Force -Path $tools | Out-Null

    Write-Host "Downloading Allure CLI $allureVersion ..."
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -Uri $url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tools -Force
    Remove-Item $zip -Force
}

if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
    Write-Host "Java не найдена. Сырые результаты: $results"
    Write-Host "Для HTML-отчёта нужна Java 17+, затем повторите .\scripts\allure-report.bat"
    exit $pytestCode
}

$allure = Find-AllureBat
if (-not $allure) {
    Install-AllureCli
    $allure = Find-AllureBat
}
if (-not $allure) {
    throw "Allure CLI не найден после установки."
}

Write-Host "Generating $report ..."
& $allure generate $results -o $report --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Opening Allure. Окно сервера можно закрыть, когда отчёт больше не нужен."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c call `"$allure`" open `"$report`"" -WorkingDirectory $root

exit $pytestCode
