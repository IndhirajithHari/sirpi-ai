param([string]$FreeCAD = $env:SIRPI_FREECAD, [int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (-not $FreeCAD) {
    $candidates = @(Get-ChildItem -Path "$env:ProgramFiles\FreeCAD*\bin\FreeCAD.exe", "$env:LOCALAPPDATA\Programs\FreeCAD*\bin\FreeCAD.exe" -ErrorAction SilentlyContinue)
    if ($candidates.Count) { $FreeCAD = $candidates[0].FullName }
}
if (-not $FreeCAD -or -not (Test-Path -LiteralPath $FreeCAD -PathType Leaf)) {
    throw 'FreeCAD was not found. Pass -FreeCAD "C:\path\to\FreeCAD.exe".'
}
$env:SIRPI_REPO = $repo
$env:SIRPI_PORT = "$Port"
# This window is the interactive CAD application the user will watch/control.
Start-Process -FilePath $FreeCAD -ArgumentList ('"' + (Join-Path $PSScriptRoot 'Sirpi.FCMacro') + '"')
Write-Host "Sirpi FreeCAD launched on port $Port. Use the Sirpi Chat panel to describe and build a part."
