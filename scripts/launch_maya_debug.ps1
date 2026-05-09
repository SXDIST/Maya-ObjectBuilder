param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$RepoRoot   = Resolve-Path (Join-Path $PSScriptRoot "..")
$PluginPath = Join-Path $RepoRoot "build\Debug\MayaObjectBuilder.mll"
$MelScript  = Join-Path $RepoRoot "build\launch_maya_debug_plugin.mel"
$Maya       = "C:\Program Files\Autodesk\Maya2027\bin\maya.exe"

if ($Build) {
    Write-Host "Building Debug plugin..."
    cmake --build (Join-Path $RepoRoot "build") --config Debug
    if ($LASTEXITCODE -ne 0) { throw "Debug build failed (exit $LASTEXITCODE)" }
}

if (-not (Test-Path $PluginPath)) {
    throw "Plugin not found: $PluginPath`nRun with -Build or build manually first."
}

if (-not (Test-Path $MelScript)) {
    throw "MEL launch script not found: $MelScript`nRun cmake configure first."
}

if (-not (Test-Path $Maya)) {
    throw "Maya 2027 not found at: $Maya"
}

Write-Host "Launching Maya 2027 with debug plugin..."
Start-Process -FilePath $Maya -ArgumentList "-script `"$MelScript`""
