$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$c4 = Join-Path $PSScriptRoot "lab5\c4"
$uml = Join-Path $PSScriptRoot "lab5\uml"
$outC4 = Join-Path $PSScriptRoot "lab5\svg"
$outUml = $outC4
New-Item -ItemType Directory -Force -Path $outC4 | Out-Null

$jar = Get-ChildItem -Path (Join-Path $root "tools") -Recurse -Filter "plantuml*.jar" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $jar) {
    Write-Host "PlantUML jar not found. Install plantuml or place jar in tools/"
    exit 1
}

java -jar $jar.FullName -tsvg -o $outC4 `
  (Join-Path $c4 "L2-container.puml") `
  (Join-Path $c4 "L3-component.puml") `
  (Join-Path $uml "class-ui-layer.puml")
Write-Host "Done: $outUml"
