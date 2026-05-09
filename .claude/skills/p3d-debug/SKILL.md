---
name: p3d-debug
description: Investigate MayaObjectBuilder P3D import/export regressions, Object Builder compatibility, TAGGs, LOD signatures, UVs, selections, proxies, mass, and axis conversion.
---

# p3d-debug

Use this for P3D bugs: bad roundtrip, Object Builder opens a broken file, missing UVs/materials/selections, wrong LOD, bad proxies, mass/flag loss, DayZ incompatibility, or Russian requests like "сломался экспорт", "проверь p3d", "почему Object Builder не видит", "проблема с TAGG/LOD/UV".

For deep format reasoning, prefer the `p3d-architect` project subagent.

## First inspect

- `src/translators/P3DTranslator.cpp`
- `src/maya/MayaMeshImport.cpp`
- `src/maya/MayaMeshExport.cpp`
- `src/formats/P3D.cpp`
- `src/formats/P3D.h`
- `tests/mayapy/p3d_workflow.py`
- `Arma3ObjectBuilder-master/Arma3ObjectBuilder/io/data_p3d.py` only as a reference, never as an edit target.

## Critical invariants

- P3D faces are triangles or quads only.
- Triangles write 16 bytes of zero padding after vertices; quads do not.
- N-gons are triangulated in `exportMeshLOD()` via Maya polygon triangles.
- UVs are stored in face data and in `#UVSet#` TAGGs.
- UV V is inverted on write and read as `1 - v`.
- `#UVSet#` ids must be 0-based; id `0` is the primary Object Builder UV set.
- Export reads Maya's current active UV set through `meshFn.getUVs()`.
- Maya Y-up to P3D position is `(x, z, y)`.
- Normals write as `-x, -z, -y`.
- TAGG layout is `active byte + null-terminated name + uint32 length + data`.
- DayZ/Object Builder compatibility wins over Arma-3-only assumptions.

## Debug flow

1. Reproduce with the smallest workflow: `p3d_roundtrip` for binary format, `mayapy p3d_workflow.py` for Maya integration.
2. Identify whether the failure is parser/writer, importer, exporter, or translator registration.
3. Compare actual data path against the invariants above.
4. Make the smallest code change in the owning layer.
5. Run the targeted test, then `/p3d-validate` if behavior changed.

## Verification commands

```bash
cmake --build build --config Debug
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

## Output format

- Root cause layer: format / import / export / translator / test.
- Relevant file and function references.
- Minimal fix direction.
- Verification run and result.
