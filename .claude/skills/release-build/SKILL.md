---
name: release-build
description: Build and validate MayaObjectBuilder release artifacts when packaging prerequisites exist; otherwise report missing release blockers clearly.
---

# release-build

Use this when the user asks to build a release, package the plugin, create a release zip, or says in Russian: "собери релиз", "сделай zip", "подготовь релиз", "упакуй плагин".

Prefer the `release-builder` project subagent.

## Required version

Ask for a version if the user did not provide one.

## Prerequisites to verify first

- `scripts/package_release.ps1`
- `install/install_maya.py`
- `MayaObjectBuilder.mod` or a documented generator/template
- `scripts/objectBuilderMenu.py`
- `scripts/mayaObjectBuilderP3DOptions.mel`
- `README.md`
- `LICENSE`

If required packaging files are missing, stop and report blockers. Do not fabricate the release package.

## Documented command

```bash
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version <version>
```

## Release flow when prerequisites exist

```bash
cmake --build build --config Release
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version <version>
```

## Expected outputs

- `dist/MayaObjectBuilder-v<version>-win64/`
- `dist/MayaObjectBuilder-v<version>-win64.zip`
- SHA256 checksum file next to the archive

## Rules

- Treat `dist/` as generated output.
- Do not edit packaging scripts or installer files unless the user asks to implement packaging.
- Do not publish GitHub releases.
- Do not push commits or tags.
- Do not claim success unless the zip and checksum exist.

## Output format

- Version.
- Prerequisite status.
- Commands run or blockers found.
- Artifact paths if created.
- Final release readiness status.
