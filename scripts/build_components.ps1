$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "components"))) {
    $root = $PSScriptRoot
}
Set-Location $root

$out = Join-Path $root "assembled"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Get-ChildItem $out -Filter "*.whl" -ErrorAction SilentlyContinue | Remove-Item -Force

py -3 -m pip install --quiet build
$names = @("wildlife_business", "wildlife_data", "wildlife_ui", "wildlife_gui", "wildlife_app")
foreach ($name in $names) {
    py -3 -m build --wheel (Join-Path $root "components\$name") --outdir $out
}

Copy-Item (Join-Path $root "config.ini") (Join-Path $out "config.ini") -Force
$runner = Join-Path $root "assembled\run.bat"
if (Test-Path $runner) {
    # run.bat already in assembled
}

Write-Host "Сборки: $out"
Get-ChildItem $out | Select-Object Name, Length
