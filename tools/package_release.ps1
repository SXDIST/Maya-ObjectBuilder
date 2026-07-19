param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"

# Pure-Python release: no compilation. Stage plug-ins/ + scripts/ + install/ and zip.
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PackageName = "MayaObjectBuilder-v$Version-win64"
$DistDir = Join-Path $RepoRoot "dist"
$StageDir = Join-Path $DistDir $PackageName
$ZipPath = Join-Path $DistDir "$PackageName.zip"

$RequiredFiles = @(
    "plug-ins/MayaObjectBuilder.py",
    "plug-ins/MayaObjectBuilderTranslator.py",
    "scripts/objectBuilderMenu.py",
    "scripts/objectBuilderAutoLOD.py",
    "scripts/mayaObjectBuilderP3DOptions.mel",
    "scripts/a3ob/__init__.py",
    "scripts/a3ob/mayabridge/commands/__init__.py",
    "scripts/a3ob/mayabridge/import_/__init__.py",
    "scripts/a3ob/mayabridge/export/__init__.py",
    "scripts/a3ob/ui/constants.py",
    "scripts/a3ob/ui/scene/__init__.py",
    "scripts/a3ob/ui/autolod/__init__.py",
    "scripts/a3ob/ui/dock.py",
    "install/mayaObjectBuilderInstall.py",
    "install/install_maya.py",
    "README.md",
    "LICENSE"
)
foreach ($RelativePath in $RequiredFiles) {
    $Path = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path $Path)) {
        throw "Required release file not found: $Path"
    }
}

if (Test-Path $StageDir) {
    Remove-Item $StageDir -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $StageDir "install") | Out-Null

# Copy plug-ins/ and scripts/ trees, excluding Python caches.
$exclude = @("__pycache__", "*.pyc", "*.pyo")
Copy-Item (Join-Path $RepoRoot "plug-ins") (Join-Path $StageDir "plug-ins") -Recurse -Exclude $exclude
Copy-Item (Join-Path $RepoRoot "scripts") (Join-Path $StageDir "scripts") -Recurse -Exclude $exclude
Get-ChildItem -Path (Join-Path $StageDir "scripts") -Recurse -Include "__pycache__" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

Copy-Item (Join-Path $RepoRoot "install/mayaObjectBuilderInstall.py") (Join-Path $StageDir "install/mayaObjectBuilderInstall.py")
Copy-Item (Join-Path $RepoRoot "install/install_maya.py") (Join-Path $StageDir "install/install_maya.py")
Copy-Item (Join-Path $RepoRoot "README.md") (Join-Path $StageDir "README.md")
Copy-Item (Join-Path $RepoRoot "LICENSE") (Join-Path $StageDir "LICENSE")

$ModuleText = @"
+ MayaObjectBuilder $Version .
MAYA_PLUG_IN_PATH +:= plug-ins
MAYA_SCRIPT_PATH +:= scripts
PYTHONPATH +:= scripts
"@
Set-Content -Path (Join-Path $StageDir "MayaObjectBuilder.mod") -Value $ModuleText -Encoding UTF8

Compress-Archive -Path $StageDir -DestinationPath $ZipPath -Force
$Hash = Get-FileHash -Algorithm SHA256 $ZipPath
Set-Content -Path (Join-Path $DistDir "$PackageName.zip.sha256") -Value "$($Hash.Hash)  $PackageName.zip" -Encoding ASCII

Write-Host "Release package staged: $StageDir"
Write-Host "Release archive created: $ZipPath"
Write-Host "SHA256: $($Hash.Hash)"
