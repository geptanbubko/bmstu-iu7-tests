# Генерация SVG для лаб. №2 (нужны Java и tools/plantuml.jar)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
java -jar "tools\plantuml.jar" -tsvg -o "diagrams\lab2\svg" `
  "diagrams\lab2\c4\L1-context.puml" `
  "diagrams\lab2\c4\L2-container.puml" `
  "diagrams\lab2\c4\L3-component.puml" `
  "diagrams\lab2\uml\class-data-layer.puml" `
  "diagrams\lab2\uml\class-business-layer.puml" `
  "diagrams\lab2\uml\seq-add-observation.puml" `
  "diagrams\lab2\uml\seq-population-analysis.puml" `
  "diagrams\lab2\uml\seq-catalog-manage.puml"
