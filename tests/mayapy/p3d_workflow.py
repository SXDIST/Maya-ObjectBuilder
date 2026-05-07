import os
from pathlib import Path

import maya.cmds as cmds
import maya.standalone


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "build" / "Debug" / "MayaObjectBuilder.mll"
INPUTS = [
    ROOT / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d" / "sample_2_crate.p3d",
    ROOT / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d" / "sample_1_character.p3d",
]
OUTDIR = ROOT / "build" / "mayapy-workflow"
DAYZ_OUTDIR = ROOT / "build" / "dayz-p3d-workflow"


def optional_dayz_inputs():
    candidates = []
    if os.environ.get("DAYZ_P3D_FIXTURES"):
        candidates.append(Path(os.environ["DAYZ_P3D_FIXTURES"]))
    candidates.extend([ROOT / "tests" / "inputs" / "dayz_p3d", ROOT / "local" / "dayz_p3d"])
    inputs = []
    for candidate in candidates:
        if candidate.exists():
            inputs.extend(sorted(candidate.glob("*.p3d")))
    return inputs


def lod_counts():
    counts = []
    for node in cmds.ls(type="transform") or []:
        if cmds.attributeQuery("a3obIsLOD", node=node, exists=True):
            counts.append((
                cmds.getAttr(node + ".a3obResolutionSignature"),
                cmds.getAttr(node + ".a3obSourceVertexCount"),
                cmds.getAttr(node + ".a3obSourceFaceCount"),
            ))
    return sorted(counts)


def proxy_selection_sets():
    names = []
    for node in cmds.ls(type="objectSet") or []:
        if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True) and cmds.getAttr(node + ".a3obIsProxySelection"):
            names.append(cmds.getAttr(node + ".a3obSelectionName"))
    return sorted(names)


def selection_names():
    names = []
    for node in cmds.ls(type="objectSet") or []:
        if cmds.attributeQuery("a3obSelectionName", node=node, exists=True):
            names.append(cmds.getAttr(node + ".a3obSelectionName"))
    return sorted(names)


def material_pairs():
    pairs = []
    for node in (cmds.ls(type="shadingEngine") or []) + (cmds.ls(materials=True) or []):
        if cmds.attributeQuery("a3obTexture", node=node, exists=True) or cmds.attributeQuery("a3obMaterial", node=node, exists=True):
            texture = cmds.getAttr(node + ".a3obTexture") if cmds.attributeQuery("a3obTexture", node=node, exists=True) else ""
            material = cmds.getAttr(node + ".a3obMaterial") if cmds.attributeQuery("a3obMaterial", node=node, exists=True) else ""
            pairs.append((texture, material))
    return sorted(set(pairs))


def uv_values(mesh):
    raw = cmds.polyEditUV(mesh + ".map[*]", query=True) or []
    pairs = []
    for index in range(0, len(raw), 2):
        pairs.append((round(float(raw[index]), 4), round(float(raw[index + 1]), 4)))
    return sorted(pairs)


def assert_generated_metadata():
    if "proxy:proxy/generated_dayz.p3d.7" not in proxy_selection_sets():
        raise RuntimeError("Generated proxy selection did not roundtrip")
    if "generated_vertex_flag" not in selection_names() or "generated_face_flag" not in selection_names():
        raise RuntimeError("Generated flag sets did not roundtrip")
    if ("dz\\weapons\\generated_ca.paa", "dz\\weapons\\generated.rvmat") not in material_pairs():
        raise RuntimeError("Generated material metadata did not roundtrip")
    lods = [node for node in cmds.ls(type="transform") or [] if cmds.attributeQuery("a3obIsLOD", node=node, exists=True)]
    if len(lods) != 1:
        raise RuntimeError(f"Expected one generated LOD, got {lods}")
    lod = lods[0]
    masses = cmds.getAttr(lod + ".a3obMassValues").split(";")
    if len(masses) != cmds.getAttr(lod + ".a3obSourceVertexCount"):
        raise RuntimeError("Generated mass count did not roundtrip")


def create_generated_fixture(path):
    cmds.file(new=True, force=True)
    lod = cmds.a3obCreateLOD(lodType=1, resolution=25, name="generated_dayz_lod")
    mesh_transform = cmds.polyPlane(name="generated_dayz_mesh", subdivisionsX=1, subdivisionsY=1)[0]
    mesh_shape = cmds.listRelatives(mesh_transform, shapes=True, fullPath=True)[0]
    cmds.parent(mesh_shape, lod, shape=True, relative=True)
    cmds.delete(mesh_transform)
    mesh = cmds.ls(cmds.listRelatives(lod, shapes=True, fullPath=True)[0], long=True)[0]
    cmds.polyEditUV(mesh + ".map[0]", u=0.125, v=0.875, relative=False)
    cmds.polyEditUV(mesh + ".map[1]", u=0.625, v=0.625, relative=False)
    cmds.polyEditUV(mesh + ".map[2]", u=0.875, v=0.375, relative=False)
    cmds.polyEditUV(mesh + ".map[3]", u=0.375, v=0.125, relative=False)

    cmds.select(mesh + ".f[0]")
    cmds.a3obSetMaterial(texture="dz\\weapons\\generated_ca.paa", material="dz\\weapons\\generated.rvmat")

    cmds.select(lod)
    cmds.a3obSetMass(value=2.5)
    cmds.select(mesh + ".vtx[0]")
    cmds.a3obSetMass(value=7.5, selectedComponents=True)
    cmds.select(mesh + ".f[0]")
    cmds.a3obProxy(path="proxy/generated_dayz.p3d", index=7, fromSelection=True)
    cmds.select(mesh + ".vtx[0:1]")
    cmds.a3obSetFlag(component="vertex", value=123, name="generated_vertex_flag")
    cmds.select(mesh + ".f[0]")
    cmds.a3obSetFlag(component="face", value=456, name="generated_face_flag")

    before_uvs = uv_values(mesh)
    cmds.select(lod)
    cmds.a3obValidate()
    cmds.file(rename=str(path))
    cmds.file(exportAll=True, force=True, type="Arma P3D")
    cmds.file(new=True, force=True)
    cmds.file(str(path), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="generated")
    assert_generated_metadata()
    imported_meshes = cmds.ls("generated:*", type="mesh") or []
    if imported_meshes and uv_values(imported_meshes[0]) != before_uvs:
        raise RuntimeError("Generated UV values changed after roundtrip")
    print("OK generated DayZ-style P3D metadata workflow")


def assert_import_hierarchy(path):
    root = "p3d:" + path.stem.replace(".", "_")
    if not cmds.objExists(root):
        raise RuntimeError(f"Missing import root {root}")
    groups = set(cmds.listRelatives(root, children=True, type="transform") or [])
    if "p3d:Visuals" not in groups:
        raise RuntimeError(f"Missing Visuals group for {path.name}")
    lod_names = set()
    for group in groups:
        lod_names.update(cmds.listRelatives(group, children=True, type="transform") or [])
    if not any("Resolution" in name for name in lod_names):
        raise RuntimeError(f"Missing human-readable visual LOD names for {path.name}")
    if any(cmds.getAttr(node + ".a3obLodType") in (6, 14, 15) for node in cmds.ls(type="transform") or [] if cmds.attributeQuery("a3obIsLOD", node=node, exists=True)) and "p3d:Geometries" not in groups:
        raise RuntimeError(f"Missing Geometries group for {path.name}")


def roundtrip_file(path, outdir):
    cmds.file(new=True, force=True)
    cmds.file(str(path), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="p3d")
    assert_import_hierarchy(path)
    before = lod_counts()
    cmds.a3obValidate()
    out = outdir / path.name
    cmds.file(rename=str(out))
    cmds.file(exportAll=True, force=True, type="Arma P3D")
    cmds.file(new=True, force=True)
    cmds.file(str(out), i=True, type="Arma P3D", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="rt")
    after = lod_counts()
    if before != after:
        raise RuntimeError(f"LOD counts changed for {path.name}: {before} != {after}")
    print(f"OK {path.name} lods={len(after)}")


def main():
    maya.standalone.initialize(name="python")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    DAYZ_OUTDIR.mkdir(parents=True, exist_ok=True)
    cmds.loadPlugin(str(PLUGIN), quiet=True)
    commands = set(cmds.pluginInfo("MayaObjectBuilder", query=True, command=True) or [])
    expected = {"a3obValidate", "a3obSetMass", "a3obSetMaterial", "a3obSetFlag", "a3obCreateLOD", "a3obProxy"}
    missing = expected - commands
    if missing:
        raise RuntimeError(f"Missing commands: {sorted(missing)}")

    cmds.file(new=True, force=True)
    lod = cmds.a3obCreateLOD(lodType=1, resolution=0, name="workflow_lod")
    mesh = cmds.polyPlane(name="workflow_mesh", subdivisionsX=1, subdivisionsY=1)[0]
    cmds.parent(mesh, lod)
    cmds.select(mesh + ".f[0]")
    cmds.a3obProxy(path="proxy/workflow.p3d", index=1, fromSelection=True)
    if "proxy:proxy/workflow.p3d.1" not in proxy_selection_sets():
        raise RuntimeError("Proxy selection set was not created")
    cmds.select(lod)
    cmds.a3obValidate()

    create_generated_fixture(OUTDIR / "generated_dayz_metadata.p3d")

    for path in INPUTS:
        roundtrip_file(path, OUTDIR)

    dayz_inputs = optional_dayz_inputs()
    if dayz_inputs:
        for path in dayz_inputs:
            roundtrip_file(path, DAYZ_OUTDIR)
    else:
        print("SKIP optional DayZ P3D fixtures: set DAYZ_P3D_FIXTURES or add tests/inputs/dayz_p3d/*.p3d")

    maya.standalone.uninitialize()


if __name__ == "__main__":
    main()
