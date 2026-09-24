$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $PSScriptRoot "lab6\svg"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$jar = Get-ChildItem -Path (Join-Path $root "tools") -Recurse -Filter "plantuml*.jar" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $jar) {
    Write-Host "PlantUML jar not found."
    exit 1
}

java -jar $jar.FullName -tsvg -o $out `
  (Join-Path $PSScriptRoot "lab6\c4\L1-context.puml") `
  (Join-Path $PSScriptRoot "lab6\c4\L2-container.puml") `
  (Join-Path $PSScriptRoot "lab6\c4\L3-component.puml") `
  (Join-Path $PSScriptRoot "lab6\uml\class-application.puml")
Write-Host "Done: $out"
