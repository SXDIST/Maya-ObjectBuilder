$ErrorActionPreference = "Stop"

# Pure-Python plugin: no build step. Register this repo as a Maya module (edit-in-place)
# and launch Maya 2027; the plugin autoloads from plug-ins/MayaObjectBuilder.py.
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Mayapy   = "C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe"
$Maya     = "C:\Program Files\Autodesk\Maya2027\bin\maya.exe"

if (-not (Test-Path $Maya)) {
    throw "Maya 2027 not found at: $Maya"
}

Write-Host "Registering MayaObjectBuilder dev module (edit-in-place)..."
& $Mayapy -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0, r'$RepoRoot/scripts'); import dev_install; dev_install.install(load=False)"

Write-Host "Launching Maya 2027 (plugin autoloads from plug-ins/MayaObjectBuilder.py)..."
Start-Process -FilePath $Maya
