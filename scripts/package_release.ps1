param(
    [string]$Version = "0.1.0",
    [string]$Configuration = "Release",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PackageName = "MayaObjectBuilder-v$Version-win64"
$DistDir = Join-Path $RepoRoot "dist"
$StageDir = Join-Path $DistDir $PackageName
$ZipPath = Join-Path $DistDir "$PackageName.zip"
$PluginPath = Join-Path $RepoRoot "build/$Configuration/MayaObjectBuilder.mll"

if (-not $SkipBuild) {
    cmake --build (Join-Path $RepoRoot "build") --config $Configuration
    if ($LASTEXITCODE -ne 0) {
        throw "Release build failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path $PluginPath)) {
    throw "Plugin binary not found: $PluginPath"
}

$RequiredFiles = @(
    "scripts/objectBuilderMenu.py",
    "scripts/objectBuilderAutoLOD.py",
    "scripts/mayaObjectBuilderP3DOptions.mel",
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
New-Item -ItemType Directory -Force -Path (Join-Path $StageDir "plug-ins") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $StageDir "scripts") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $StageDir "install") | Out-Null

Copy-Item $PluginPath (Join-Path $StageDir "plug-ins/MayaObjectBuilder.mll")
Copy-Item (Join-Path $RepoRoot "scripts/objectBuilderMenu.py") (Join-Path $StageDir "scripts/objectBuilderMenu.py")
Copy-Item (Join-Path $RepoRoot "scripts/objectBuilderAutoLOD.py") (Join-Path $StageDir "scripts/objectBuilderAutoLOD.py")
Copy-Item (Join-Path $RepoRoot "scripts/mayaObjectBuilderP3DOptions.mel") (Join-Path $StageDir "scripts/mayaObjectBuilderP3DOptions.mel")
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
