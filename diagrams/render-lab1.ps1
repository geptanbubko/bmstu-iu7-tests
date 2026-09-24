# Генерация SVG для лаб. №1
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\diagrams\lab1"
java -jar "..\..\tools\plantuml.jar" -tsvg *.puml
