$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $PSScriptRoot "lab3\svg"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$uml = Join-Path $PSScriptRoot "lab3\uml\class-business-layer.puml"
$jar = Get-ChildItem -Path (Join-Path $root "tools") -Recurse -Filter "plantuml*.jar" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $jar) {
    Write-Host "PlantUML jar not found. Install plantuml or place jar in tools/"
    exit 1
}

java -jar $jar.FullName -tsvg -o $out $uml
Write-Host "Done: $out\class-business-layer.svg"
